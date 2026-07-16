import pytest

from src.generator import artigo


def test_slugify_remove_acentos_e_normaliza():
    assert artigo.slugify("Conciliação Bancária da Igreja") == "conciliacao-bancaria-da-igreja"
    assert artigo.slugify("Gestão  Financeira!") == "gestao-financeira"


def test_slugify_trunca_em_fronteira_de_palavra():
    slug = artigo.slugify("palavra " * 30, max_chars=20)
    assert len(slug) <= 20
    assert not slug.endswith("-")


def _post_valido() -> dict:
    conteudo = (
        "## Primeira seção\n\n"
        "A conciliação bancária da igreja é essencial. " + ("palavra " * 620) + "\n\n"
        "## Segunda seção\n\n"
        "- item um\n- item dois\n\n"
        "Veja os [recursos do Semeio](/funcionalidades) e os [planos](/precos).\n"
    )
    return artigo._montar_post({
        "palavra_chave": "conciliação bancária da igreja",
        "titulo": "Conciliação bancária da igreja: guia prático",
        "slug": "conciliacao-bancaria-da-igreja",
        "resumo": "Aprenda a fazer a conciliação bancária da igreja com um passo a passo simples e seguro que garante transparência, ordem e confiança na tesouraria local.",
        "conteudo": conteudo,
        "capa_alt": "Tesoureiro conferindo extrato bancário",
        "seo_titulo": "Conciliação bancária da igreja",
        "seo_descricao": "Guia de conciliação bancária.",
        "tags": ["tesouraria", "conciliação bancária"],
    })


def test_montar_post_define_status_publicado_e_slug_normalizado():
    post = artigo._montar_post({"titulo": "Título de Teste", "slug": "Título de Teste"})
    assert post["status"] == "Publicado"
    assert post["slug"] == "titulo-de-teste"


def test_montar_post_usa_resumo_como_seo_descricao_padrao():
    post = artigo._montar_post({"titulo": "T", "resumo": "meu resumo"})
    assert post["seo_descricao"] == "meu resumo"


def test_validar_post_aceita_post_bem_formado():
    artigo._validar_post(_post_valido())  # não deve levantar


def test_validar_post_rejeita_h1_no_conteudo():
    post = _post_valido()
    post["conteudo"] = "# Título indevido\n\n" + post["conteudo"]
    with pytest.raises(ValueError, match="H1"):
        artigo._validar_post(post)


def test_validar_post_rejeita_salto_de_heading():
    post = _post_valido()
    # Mantém as 2 seções H2 e adiciona um H4 que pula o nível H3.
    post["conteudo"] += "\n\n#### Subseção com salto indevido\n\nTexto."
    with pytest.raises(ValueError, match="[Ss]alto"):
        artigo._validar_post(post)


def test_validar_post_rejeita_conteudo_curto():
    post = _post_valido()
    post["conteudo"] = "## Seção\n\nTexto curto.\n\n## Outra\n\n[link](/precos)"
    with pytest.raises(ValueError, match="palavras"):
        artigo._validar_post(post)


def test_validar_post_rejeita_sem_link_interno():
    post = _post_valido()
    post["conteudo"] = post["conteudo"].replace("(/funcionalidades)", "(https://externo.com)").replace("(/precos)", "(https://externo.com)")
    with pytest.raises(ValueError, match="link interno"):
        artigo._validar_post(post)


def test_validar_post_rejeita_poucas_tags():
    post = _post_valido()
    post["tags"] = ["única"]
    with pytest.raises(ValueError, match="tags"):
        artigo._validar_post(post)


def test_validar_post_rejeita_resumo_longo_demais():
    post = _post_valido()
    post["resumo"] = "x" * 281
    with pytest.raises(ValueError, match="[Rr]esumo"):
        artigo._validar_post(post)


def test_artigos_do_tema_mais_relevante_filtra_por_maior_peso():
    artigos = [
        {"peso": 3, "titulo": "a"},
        {"peso": 1, "titulo": "b"},
        {"peso": 3, "titulo": "c"},
    ]
    rel = artigo._artigos_do_tema_mais_relevante(artigos)
    assert {a["titulo"] for a in rel} == {"a", "c"}
