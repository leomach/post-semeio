import json

from src.scraper import corpus as corpus_mod


def _artigo(url, corpo="corpo", titulo="T", peso=1, fonte="F", data=None):
    return {"url": url, "titulo": titulo, "corpo": corpo, "peso": peso, "fonte": fonte, "data": data}


def test_carregar_corpus_inexistente(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus_mod, "CORPUS_PATH", tmp_path / "corpus.json")
    assert corpus_mod.carregar_corpus() == {"artigos": {}}


def test_salvar_e_carregar_ciclo_completo(tmp_path, monkeypatch):
    caminho = tmp_path / "sub" / "corpus.json"
    monkeypatch.setattr(corpus_mod, "CORPUS_PATH", caminho)

    corpus = {"artigos": {}}
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a"))
    corpus_mod.salvar_corpus(corpus)

    assert caminho.exists()
    recarregado = corpus_mod.carregar_corpus()
    assert recarregado == corpus
    with open(caminho, encoding="utf-8") as f:
        assert len(json.load(f)["artigos"]) == 1


def test_registrar_artigo_upsert_por_url_normalizada():
    corpus = {"artigos": {}}
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a/"))
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a?utm_source=x"))
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a"))
    assert len(corpus["artigos"]) == 1  # URLs equivalentes → uma entrada


def test_registrar_preserva_adicionado_em_e_mantem_maior_peso():
    corpus = {"artigos": {}}
    h = corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a", peso=2))
    adicionado_em = corpus["artigos"][h]["adicionado_em"]

    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a", peso=5, corpo="novo"))
    assert corpus["artigos"][h]["adicionado_em"] == adicionado_em  # preservado
    assert corpus["artigos"][h]["peso"] == 5  # max
    assert corpus["artigos"][h]["corpo"] == "novo"  # corpo atualizado

    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a", peso=1))
    assert corpus["artigos"][h]["peso"] == 5  # não regride


def test_em_corpus_respeita_normalizacao():
    corpus = {"artigos": {}}
    assert corpus_mod.em_corpus("https://ex.com/a", corpus) is False
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a"))
    assert corpus_mod.em_corpus("https://ex.com/a/", corpus) is True
    assert corpus_mod.em_corpus("https://ex.com/a?fbclid=z", corpus) is True


def test_podar_remove_mais_antigos_deterministico():
    corpus = {"artigos": {}}
    # Injeta com adicionado_em controlado para ordem determinística.
    for i, ts in enumerate(["2026-01-01", "2026-02-01", "2026-03-01"]):
        h = corpus_mod.registrar_artigo(corpus, _artigo(f"https://ex.com/{i}"))
        corpus["artigos"][h]["adicionado_em"] = ts

    removidos = corpus_mod.podar_corpus(corpus, max_artigos=2)
    assert removidos == 1
    urls = {a["url"] for a in corpus_mod.artigos(corpus)}
    assert urls == {"https://ex.com/1", "https://ex.com/2"}  # o de jan/2026 saiu


def test_podar_sem_excedente_nao_remove():
    corpus = {"artigos": {}}
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a"))
    assert corpus_mod.podar_corpus(corpus, max_artigos=10) == 0


def test_tolera_data_none():
    corpus = {"artigos": {}}
    corpus_mod.registrar_artigo(corpus, _artigo("https://ex.com/a", data=None))
    assert corpus_mod.artigos(corpus)[0]["data"] is None
