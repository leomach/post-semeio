import pytest

from src.generator import selecao
from src.scraper.fontes import PalavraChave

PALAVRAS = [
    PalavraChave("tesouraria", 3, "rotina-financeira"),
    PalavraChave("prestação de contas", 3, "rotina-financeira"),
    PalavraChave("imunidade tributária", 3, "fiscal-tributario"),
    PalavraChave("LGPD", 2, "fiscal-tributario"),
    PalavraChave("mordomia cristã", 3, "teologia-mordomia"),
    PalavraChave("dízimo", 2, "teologia-mordomia"),
]


def _artigo(titulo, corpo="", peso=3, data=None, url=None):
    return {"titulo": titulo, "corpo": corpo, "peso": peso, "data": data, "url": url or titulo}


def _hist(*eixo_angulo):
    """Monta historico_posts a partir de pares (eixo, angulo)."""
    return {"historico_posts": [{"eixo": e, "angulo": a} for e, a in eixo_angulo]}


def test_seleciona_angulo_com_lastro_basico():
    corpus = [_artigo("Guia", corpo="a tesouraria da igreja precisa de ordem")]
    eixo, angulo, suporte = selecao.selecionar_angulo(corpus, PALAVRAS, {}, cooldown_posts=3)
    assert angulo == "tesouraria"
    assert eixo == "rotina-financeira"
    assert len(suporte) == 1


def test_prioriza_angulo_nunca_publicado_sobre_maior_score():
    corpus = [
        _artigo("A", corpo="tesouraria tesouraria tesouraria", url="a"),  # score alto
        _artigo("B", corpo="LGPD nas igrejas", url="b"),
    ]
    estado = _hist(("rotina-financeira", "tesouraria"))  # tesouraria já publicada
    _, angulo, _ = selecao.selecionar_angulo(corpus, PALAVRAS, estado, cooldown_posts=0)
    assert angulo == "LGPD"  # inédito vence, mesmo com score menor


def test_respeita_cooldown_de_eixo():
    corpus = [
        _artigo("A", corpo="tesouraria e prestação de contas", url="a"),
        _artigo("B", corpo="imunidade tributária da igreja", url="b"),
    ]
    estado = _hist(("rotina-financeira", "tesouraria"))
    eixo, _, _ = selecao.selecionar_angulo(corpus, PALAVRAS, estado, cooldown_posts=3)
    assert eixo == "fiscal-tributario"  # rotina-financeira está em cooldown


def test_lru_entre_angulos_ja_publicados():
    corpus = [_artigo("A", corpo="tesouraria e LGPD", url="a")]
    # ambos publicados; tesouraria é o mais antigo
    estado = _hist(("rotina-financeira", "tesouraria"), ("fiscal-tributario", "LGPD"))
    _, angulo, _ = selecao.selecionar_angulo(corpus, PALAVRAS, estado, cooldown_posts=0)
    assert angulo == "tesouraria"  # menos recente


def test_desempata_por_score_quando_ambos_ineditos():
    corpus = [_artigo("A", corpo="tesouraria; imunidade tributária imunidade tributária", url="a")]
    _, angulo, _ = selecao.selecionar_angulo(corpus, PALAVRAS, {}, cooldown_posts=3)
    # imunidade tributária: 2 ocorrências × peso 3 = 6 > tesouraria: 1 × 3 = 3
    assert angulo == "imunidade tributária"


def test_garante_angulo_mesmo_com_todos_eixos_em_cooldown():
    corpus = [_artigo("A", corpo="tesouraria da igreja", url="a")]
    estado = _hist(("rotina-financeira", "tesouraria"))
    # rotina em cooldown e é o único eixo com material: relaxa e ainda devolve um ângulo.
    eixo, angulo, _ = selecao.selecionar_angulo(corpus, PALAVRAS, estado, cooldown_posts=3)
    assert eixo == "rotina-financeira"
    assert angulo == "tesouraria"


def test_prefere_material_fresco_sobre_corpus():
    corpus = [_artigo("velho", corpo="tesouraria tesouraria tesouraria", url="velho")]  # score 9
    frescos = [_artigo("novo", corpo="LGPD nas igrejas", url="novo")]  # score 2
    _, angulo, suporte = selecao.selecionar_angulo(
        corpus, PALAVRAS, {}, cooldown_posts=0, fresh_artigos=frescos
    )
    assert angulo == "LGPD"  # fresco preferido apesar do score menor
    assert suporte[0]["url"] == "novo"


def test_cai_no_corpus_quando_fresco_nao_tem_angulo_elegivel():
    corpus = [_artigo("c", corpo="tesouraria da igreja", url="c")]  # rotina (não em cooldown)
    frescos = [_artigo("f", corpo="LGPD nas igrejas", url="f")]  # fiscal (em cooldown)
    estado = _hist(("fiscal-tributario", "imunidade tributária"))
    eixo, angulo, suporte = selecao.selecionar_angulo(
        corpus, PALAVRAS, estado, cooldown_posts=3, fresh_artigos=frescos
    )
    assert eixo == "rotina-financeira"
    assert angulo == "tesouraria"
    assert suporte[0]["url"] == "c"


def test_min_suporte_exclui_angulo_com_pouco_lastro():
    corpus = [
        _artigo("A", corpo="tesouraria", url="a"),  # 1 artigo p/ tesouraria
        _artigo("B", corpo="LGPD para igrejas", url="b"),  # 2 artigos p/ LGPD
        _artigo("C", corpo="LGPD e proteção de dados", url="c"),
    ]
    _, angulo, _ = selecao.selecionar_angulo(
        corpus, PALAVRAS, {}, cooldown_posts=0, min_suporte=2
    )
    assert angulo == "LGPD"  # tesouraria excluída por ter só 1 artigo de suporte


def test_top_k_limita_artigos_de_suporte():
    corpus = [_artigo(f"A{i}", corpo="tesouraria da igreja", url=f"a{i}") for i in range(5)]
    _, _, suporte = selecao.selecionar_angulo(
        corpus, PALAVRAS, {}, cooldown_posts=3, top_k=2
    )
    assert len(suporte) == 2


def test_budget_de_chars_limita_suporte():
    corpus = [_artigo(f"A{i}", corpo="tesouraria " + "x" * 100, url=f"a{i}") for i in range(5)]
    _, _, suporte = selecao.selecionar_angulo(
        corpus, PALAVRAS, {}, cooldown_posts=3, top_k=5, max_chars=150
    )
    # cada corpo tem ~111 chars; com teto 150 só cabe 1 (o primeiro sempre entra)
    assert len(suporte) == 1


def test_nao_muta_os_dicts_de_entrada():
    artigo = _artigo("A", corpo="tesouraria da igreja", url="a")
    selecao.selecionar_angulo([artigo], PALAVRAS, {}, cooldown_posts=3)
    assert "eixo" not in artigo  # a seleção antiga injetava artigo["eixo"] — não deve mais


def test_excluir_angulos_pula_termo():
    corpus = [_artigo("A", corpo="tesouraria tesouraria; LGPD", url="a")]
    _, angulo, _ = selecao.selecionar_angulo(
        corpus, PALAVRAS, {}, cooldown_posts=0, excluir_angulos=frozenset({"tesouraria"})
    )
    assert angulo == "LGPD"


def test_sem_material_levanta_valueerror():
    with pytest.raises(ValueError):
        selecao.selecionar_angulo([], PALAVRAS, {}, cooldown_posts=3)


def test_material_sem_match_levanta_valueerror():
    corpus = [_artigo("A", corpo="assunto totalmente fora do escopo", url="a")]
    with pytest.raises(ValueError):
        selecao.selecionar_angulo(corpus, PALAVRAS, {}, cooldown_posts=3)
