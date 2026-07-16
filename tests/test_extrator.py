import httpx
import pytest

from src.scraper import extrator
from src.scraper.fontes import Fonte, PalavraChave

HTML_LISTAGEM = """
<html><body>
  <a href="/artigos/tesouraria-na-pratica">Tesouraria na prática: dicas essenciais</a>
  <a href="/artigos/dizimo-e-oferta">Entendendo o dízimo na igreja local</a>
  <a href="/sobre">Sobre nós</a>
  <a href="https://outro-dominio.com/artigo">Artigo de outro site</a>
</body></html>
"""

FONTE = Fonte(nome="Fonte Teste", url_base="https://exemplo.com/blog", ativo=True)
PALAVRAS_CHAVE = [
    PalavraChave(termo="tesouraria", peso=3),
    PalavraChave(termo="dízimo", peso=2),
]


def test_extrair_links_candidatos_filtra_por_palavra_chave_e_dominio(monkeypatch):
    monkeypatch.setattr(extrator, "_buscar_html", lambda url: HTML_LISTAGEM)

    candidatos = extrator.extrair_links_candidatos(FONTE, PALAVRAS_CHAVE)
    urls = [url for url, _ in candidatos]

    assert "https://exemplo.com/artigos/tesouraria-na-pratica" in urls
    assert "https://exemplo.com/artigos/dizimo-e-oferta" in urls
    assert "https://exemplo.com/sobre" not in urls
    assert "https://outro-dominio.com/artigo" not in urls


def test_extrair_links_candidatos_rankeia_por_peso(monkeypatch):
    monkeypatch.setattr(extrator, "_buscar_html", lambda url: HTML_LISTAGEM)

    candidatos = extrator.extrair_links_candidatos(FONTE, PALAVRAS_CHAVE)
    pesos = dict(candidatos)

    assert pesos["https://exemplo.com/artigos/tesouraria-na-pratica"] == 3
    assert pesos["https://exemplo.com/artigos/dizimo-e-oferta"] == 2


def test_circuit_breaker_para_apos_falhas_consecutivas(monkeypatch):
    chamadas = []

    def _extrair_com_falha(url):
        chamadas.append(url)
        raise RuntimeError("falha simulada de rede")

    monkeypatch.setattr(extrator, "pode_acessar", lambda url: True)
    monkeypatch.setattr(
        extrator,
        "extrair_links_candidatos",
        lambda fonte, palavras_chave: [
            ("https://exemplo.com/a", 3),
            ("https://exemplo.com/b", 3),
            ("https://exemplo.com/c", 3),
            ("https://exemplo.com/d", 3),
            ("https://exemplo.com/e", 3),
        ],
    )
    monkeypatch.setattr(extrator, "extrair_conteudo", _extrair_com_falha)

    artigos = extrator.processar_fonte(
        FONTE, PALAVRAS_CHAVE, ja_processado_fn=lambda url: False, max_falhas_consecutivas=3
    )

    assert artigos == []
    assert len(chamadas) == 3  # não deve tentar os 5 links, apenas até o limite do circuit breaker


def test_processar_fonte_pula_links_ja_processados(monkeypatch):
    monkeypatch.setattr(extrator, "pode_acessar", lambda url: True)
    monkeypatch.setattr(
        extrator,
        "extrair_links_candidatos",
        lambda fonte, palavras_chave: [("https://exemplo.com/ja-visto", 3)],
    )

    def _falha_se_chamado(url):
        raise AssertionError("não deveria extrair link já processado")

    monkeypatch.setattr(extrator, "extrair_conteudo", _falha_se_chamado)

    artigos = extrator.processar_fonte(
        FONTE, PALAVRAS_CHAVE, ja_processado_fn=lambda url: True, max_falhas_consecutivas=3
    )

    assert artigos == []


def test_processar_fonte_robots_bloqueia_fonte(monkeypatch):
    monkeypatch.setattr(extrator, "pode_acessar", lambda url: False)

    def _falha_se_chamado(fonte, palavras_chave):
        raise AssertionError("não deveria buscar listagem se robots.txt bloqueia")

    monkeypatch.setattr(extrator, "extrair_links_candidatos", _falha_se_chamado)

    artigos = extrator.processar_fonte(
        FONTE, PALAVRAS_CHAVE, ja_processado_fn=lambda url: False, max_falhas_consecutivas=3
    )

    assert artigos == []


def test_rate_limit_aguarda_intervalo_minimo_entre_requisicoes_ao_mesmo_dominio(monkeypatch):
    extrator._ultima_requisicao_por_dominio.clear()

    tempos = iter([100.0, 101.0])
    monkeypatch.setattr(extrator.time, "monotonic", lambda: next(tempos))

    esperas = []
    monkeypatch.setattr(extrator.time, "sleep", lambda segundos: esperas.append(segundos))
    monkeypatch.setattr(extrator, "RATE_LIMIT_SECONDS", 4)

    extrator._respeitar_rate_limit("https://exemplo.com/pagina-1")
    extrator._respeitar_rate_limit("https://exemplo.com/pagina-2")

    assert esperas == [3.0]  # 4s de limite - 1s decorrido


def test_pode_acessar_assume_permitido_quando_robots_txt_falha(monkeypatch):
    extrator._robots_cache.clear()

    def _get_com_falha(*args, **kwargs):
        raise OSError("timeout")

    monkeypatch.setattr(extrator.httpx, "get", _get_com_falha)

    assert extrator.pode_acessar("https://site-fora-do-ar.com/pagina") is True


def test_pode_acessar_trata_403_no_robots_txt_como_falha_de_leitura_nao_bloqueio(monkeypatch):
    extrator._robots_cache.clear()

    class RespostaFake:
        status_code = 403

        def raise_for_status(self):
            raise httpx.HTTPStatusError("403", request=None, response=self)

    monkeypatch.setattr(extrator.httpx, "get", lambda *a, **k: RespostaFake())

    assert extrator.pode_acessar("https://bloqueia-ua-generico.com/blog/") is True
