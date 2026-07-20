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
    monkeypatch.setattr(extrator, "_buscar_html", lambda url, user_agent=None: HTML_LISTAGEM)

    candidatos = extrator.extrair_links_candidatos(FONTE, PALAVRAS_CHAVE)
    urls = [url for url, _ in candidatos]

    assert "https://exemplo.com/artigos/tesouraria-na-pratica" in urls
    assert "https://exemplo.com/artigos/dizimo-e-oferta" in urls
    assert "https://exemplo.com/sobre" not in urls
    assert "https://outro-dominio.com/artigo" not in urls


def test_extrair_links_candidatos_rankeia_por_peso(monkeypatch):
    monkeypatch.setattr(extrator, "_buscar_html", lambda url, user_agent=None: HTML_LISTAGEM)

    candidatos = extrator.extrair_links_candidatos(FONTE, PALAVRAS_CHAVE)
    pesos = dict(candidatos)

    assert pesos["https://exemplo.com/artigos/tesouraria-na-pratica"] == 3
    assert pesos["https://exemplo.com/artigos/dizimo-e-oferta"] == 2


def test_circuit_breaker_para_apos_falhas_consecutivas(monkeypatch):
    chamadas = []

    def _extrair_com_falha(url, user_agent=None):
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


HTML_COM_DOWNLOADS = """
<html><body>
  <a href="/artigos/tesouraria-na-pratica">Tesouraria na prática</a>
  <a href="/downloads/modelo_pc.xls">Planilha de tesouraria (modelo)</a>
  <a href="/downloads/carta_pastoral.pdf">Carta pastoral sobre dízimo</a>
  <a href="/downloads/RECIBO_CONGRUA.XLSX">Recibo de côngrua pastoral</a>
</body></html>
"""


def test_extrair_links_candidatos_descarta_links_de_download(monkeypatch):
    monkeypatch.setattr(extrator, "_buscar_html", lambda url, user_agent=None: HTML_COM_DOWNLOADS)

    candidatos = extrator.extrair_links_candidatos(FONTE, PALAVRAS_CHAVE)
    urls = [url for url, _ in candidatos]

    assert "https://exemplo.com/artigos/tesouraria-na-pratica" in urls
    # apesar de casarem palavras-chave, os arquivos binários não viram candidatos
    assert not any(u.lower().endswith((".xls", ".xlsx", ".pdf")) for u in urls)


def test_erro_recuperavel_distingue_transitorio_de_permanente():
    def _erro_status(codigo):
        resposta = httpx.Response(codigo, request=httpx.Request("GET", "https://x"))
        return httpx.HTTPStatusError("erro", request=resposta.request, response=resposta)

    assert extrator._erro_recuperavel(_erro_status(503)) is True
    assert extrator._erro_recuperavel(_erro_status(429)) is True
    assert extrator._erro_recuperavel(httpx.ConnectTimeout("timeout")) is True
    assert extrator._erro_recuperavel(_erro_status(403)) is False
    assert extrator._erro_recuperavel(_erro_status(404)) is False
    assert extrator._erro_recuperavel(extrator.ConteudoNaoHTML("pdf")) is False


class _RespostaHTTPFake:
    def __init__(self, texto="<html></html>", content_type="text/html; charset=utf-8"):
        self.text = texto
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        return None


class _ClientFake:
    def __init__(self, resposta, registro):
        self._resposta = resposta
        self._registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        return self._resposta


def test_buscar_html_rejeita_content_type_nao_html(monkeypatch):
    monkeypatch.setattr(extrator, "_respeitar_rate_limit", lambda url: None)
    resposta = _RespostaHTTPFake(texto="%PDF-1.7", content_type="application/pdf")
    monkeypatch.setattr(
        extrator.httpx, "Client", lambda **kwargs: _ClientFake(resposta, kwargs)
    )

    with pytest.raises(extrator.ConteudoNaoHTML):
        extrator._buscar_html("https://exemplo.com/arquivo.pdf")


def test_buscar_html_usa_user_agent_da_fonte(monkeypatch):
    monkeypatch.setattr(extrator, "_respeitar_rate_limit", lambda url: None)
    capturado = {}

    def _client_fake(**kwargs):
        capturado.update(kwargs.get("headers", {}))
        return _ClientFake(_RespostaHTTPFake(), kwargs)

    monkeypatch.setattr(extrator.httpx, "Client", _client_fake)

    extrator._buscar_html("https://exemplo.com/", user_agent="UA-Navegador/1.0")
    assert capturado["User-Agent"] == "UA-Navegador/1.0"


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
