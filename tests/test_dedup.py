import json

from src.scraper import dedup


def test_normalizar_url_remove_utm_e_tracking():
    url = "https://Exemplo.com/artigo/?utm_source=fb&utm_medium=post&fbclid=abc123&ref=x"
    assert dedup.normalizar_url(url) == "https://exemplo.com/artigo?ref=x"


def test_normalizar_url_remove_trailing_slash():
    assert dedup.normalizar_url("https://exemplo.com/artigo/") == "https://exemplo.com/artigo"
    assert dedup.normalizar_url("https://exemplo.com/") == "https://exemplo.com/"


def test_normalizar_url_urls_equivalentes_geram_mesma_url():
    a = dedup.normalizar_url("https://exemplo.com/post?utm_campaign=x&gclid=y")
    b = dedup.normalizar_url("https://exemplo.com/post")
    assert a == b


def test_calcular_hash_e_deterministico():
    url_normalizada = dedup.normalizar_url("https://exemplo.com/artigo")
    assert dedup.calcular_hash(url_normalizada) == dedup.calcular_hash(url_normalizada)


def test_calcular_hash_urls_diferentes_geram_hashes_diferentes():
    h1 = dedup.calcular_hash(dedup.normalizar_url("https://exemplo.com/a"))
    h2 = dedup.calcular_hash(dedup.normalizar_url("https://exemplo.com/b"))
    assert h1 != h2


def test_carregar_estado_arquivo_inexistente(tmp_path, monkeypatch):
    caminho = tmp_path / "estado.json"
    monkeypatch.setattr(dedup, "ESTADO_PATH", caminho)
    estado = dedup.carregar_estado()
    assert estado == {"links_processados": {}}


def test_salvar_e_carregar_estado_ciclo_completo(tmp_path, monkeypatch):
    caminho = tmp_path / "sub" / "estado.json"
    monkeypatch.setattr(dedup, "ESTADO_PATH", caminho)

    estado = {"links_processados": {}}
    dedup.registrar_processado("https://exemplo.com/artigo", "Fonte X", "Título X", estado)
    dedup.salvar_estado(estado)

    assert caminho.exists()
    recarregado = dedup.carregar_estado()
    assert recarregado == estado

    with open(caminho, encoding="utf-8") as f:
        bruto = json.load(f)
    assert len(bruto["links_processados"]) == 1


def test_ja_processado_detecta_link_registrado():
    estado = {"links_processados": {}}
    url = "https://exemplo.com/artigo?utm_source=x"
    assert dedup.ja_processado(url, estado) is False

    dedup.registrar_processado(url, "Fonte X", "Título", estado)

    assert dedup.ja_processado("https://exemplo.com/artigo", estado) is True
    assert dedup.ja_processado("https://exemplo.com/artigo/", estado) is True


def test_registrar_post_publicado_anexa_ao_historico():
    estado = {}
    dedup.registrar_post_publicado(estado, "rotina-financeira", "conciliação bancária", "Título")

    assert len(estado["historico_posts"]) == 1
    entrada = estado["historico_posts"][0]
    assert entrada["eixo"] == "rotina-financeira"
    assert entrada["palavra_chave"] == "conciliação bancária"
    assert entrada["titulo"] == "Título"
    assert "publicado_em" in entrada


def test_eixos_recentes_retorna_ultimos_n_em_ordem_cronologica():
    estado = {}
    for eixo in ("a", "b", "c", "d"):
        dedup.registrar_post_publicado(estado, eixo, "pc", "t")

    assert dedup.eixos_recentes(estado, 3) == ["b", "c", "d"]
    assert dedup.eixos_recentes(estado, 0) == []
    assert dedup.eixos_recentes({}, 3) == []
