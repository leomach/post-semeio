import pytest

from src.generator import selecao
from src.scraper.fontes import PalavraChave

PALAVRAS = [
    PalavraChave("tesouraria", 3, "rotina-financeira"),
    PalavraChave("prestação de contas", 3, "rotina-financeira"),
    PalavraChave("imunidade tributária", 3, "fiscal-tributario"),
    PalavraChave("mordomia cristã", 3, "teologia-mordomia"),
    PalavraChave("dízimo", 2, "teologia-mordomia"),
]


def _artigo(titulo, corpo="", peso=3, data=None):
    return {"titulo": titulo, "corpo": corpo, "peso": peso, "data": data}


def test_classificar_eixo_escolhe_eixo_dominante():
    artigo = _artigo(
        "Conciliação da igreja",
        corpo="A tesouraria cuida da prestação de contas mensal.",
    )
    assert selecao.classificar_eixo(artigo, PALAVRAS) == "rotina-financeira"


def test_classificar_eixo_sem_match_retorna_padrao():
    artigo = _artigo("Assunto totalmente fora do escopo", corpo="texto qualquer")
    assert selecao.classificar_eixo(artigo, PALAVRAS) == selecao.EIXO_PADRAO


def test_selecionar_pauta_evita_eixo_em_cooldown():
    artigos = [
        _artigo("Conciliação", corpo="tesouraria e prestação de contas", peso=6),
        _artigo("Imunidade", corpo="imunidade tributária da igreja", peso=3),
    ]
    estado = {"historico_posts": [{"eixo": "rotina-financeira"}]}

    eixo, escolhidos = selecao.selecionar_pauta(artigos, PALAVRAS, estado, cooldown_posts=3)

    assert eixo == "fiscal-tributario"
    assert escolhidos[0]["titulo"] == "Imunidade"


def test_selecionar_pauta_prioriza_eixo_nunca_publicado_sobre_peso():
    artigos = [
        _artigo("Conciliação", corpo="tesouraria e prestação de contas", peso=6),
        _artigo("Mordomia", corpo="mordomia cristã e dízimo", peso=3),
    ]
    # rotina-financeira já foi publicada antes (mas fora do cooldown); teologia nunca.
    estado = {"historico_posts": [{"eixo": "rotina-financeira"}]}

    eixo, _ = selecao.selecionar_pauta(artigos, PALAVRAS, estado, cooldown_posts=0)

    assert eixo == "teologia-mordomia"


def test_selecionar_pauta_desempata_por_peso_quando_ambos_ineditos():
    artigos = [
        _artigo("Conciliação", corpo="tesouraria e prestação de contas", peso=6),
        _artigo("Imunidade", corpo="imunidade tributária", peso=3),
    ]
    estado = {}

    eixo, _ = selecao.selecionar_pauta(artigos, PALAVRAS, estado, cooldown_posts=3)

    assert eixo == "rotina-financeira"


def test_selecionar_pauta_todos_em_cooldown_reaproveita_menos_recente():
    artigos = [
        _artigo("Conciliação", corpo="tesouraria", peso=6),
        _artigo("Imunidade", corpo="imunidade tributária", peso=3),
    ]
    # Ordem cronológica: rotina-financeira foi o mais antigo, fiscal o mais recente.
    estado = {
        "historico_posts": [
            {"eixo": "rotina-financeira"},
            {"eixo": "fiscal-tributario"},
        ]
    }

    eixo, _ = selecao.selecionar_pauta(artigos, PALAVRAS, estado, cooldown_posts=3)

    assert eixo == "rotina-financeira"


def test_selecionar_pauta_agrupa_artigos_do_eixo_ordenados_por_relevancia():
    artigos = [
        _artigo("Menor", corpo="tesouraria", peso=3, data="2026-01-01"),
        _artigo("Maior", corpo="prestação de contas", peso=6, data="2026-02-01"),
        _artigo("Outro eixo", corpo="imunidade tributária", peso=9),
    ]
    estado = {"historico_posts": [{"eixo": "fiscal-tributario"}]}

    eixo, escolhidos = selecao.selecionar_pauta(artigos, PALAVRAS, estado, cooldown_posts=3)

    assert eixo == "rotina-financeira"
    assert [a["titulo"] for a in escolhidos] == ["Maior", "Menor"]


def test_selecionar_pauta_sem_artigos_levanta_erro():
    with pytest.raises(ValueError):
        selecao.selecionar_pauta([], PALAVRAS, {}, cooldown_posts=3)
