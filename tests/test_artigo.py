import json

import pytest

from src.generator import artigo
from src.scraper.fontes import PalavraChave

PALAVRAS = [
    PalavraChave("tesouraria", 3, "rotina-financeira"),
    PalavraChave("imunidade tributária", 6, "fiscal-tributario"),
]


def _dados_validos() -> dict:
    conteudo = (
        "## Primeira seção\n\n"
        "A conciliação bancária da igreja é essencial. " + ("palavra " * 620) + "\n\n"
        "## Segunda seção\n\n"
        "Veja os [recursos do Semeio](/funcionalidades) e os [planos](/precos).\n"
    )
    return {
        "palavra_chave": "conciliação bancária da igreja",
        "titulo": "Conciliação bancária da igreja: guia prático",
        "slug": "conciliacao-bancaria-da-igreja",
        "resumo": "Aprenda a fazer a conciliação bancária da igreja com um passo a passo simples e seguro que garante transparência, ordem e confiança na tesouraria local.",
        "conteudo": conteudo,
        "capa_alt": "Tesoureiro conferindo extrato bancário",
        "seo_titulo": "Conciliação bancária da igreja",
        "seo_descricao": "Guia de conciliação bancária.",
        "tags": ["tesouraria", "conciliação bancária"],
    }


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


def _corpus_tesouraria():
    return [{"url": "a", "titulo": "Tesouraria", "corpo": "tesouraria da igreja", "peso": 3, "data": None}]


def test_gerar_post_blog_passa_angulo_ao_prompt_e_retorna_tupla(monkeypatch, tmp_path):
    prompts = []

    def fake_gerar(prompt):
        prompts.append(prompt)
        return "contexto unificado" if len(prompts) == 1 else json.dumps(_dados_validos())

    monkeypatch.setattr(artigo, "gerar", fake_gerar)
    monkeypatch.setattr(artigo, "POST_BLOG_PATH", tmp_path / "post.json")
    monkeypatch.setattr(artigo, "ARTIGO_PATH", tmp_path / "artigo.md")

    post, eixo, angulo = artigo.gerar_post_blog(
        _corpus_tesouraria(), [], PALAVRAS, {}, cooldown_posts=3
    )

    assert (eixo, angulo) == ("rotina-financeira", "tesouraria")
    # o ângulo escolhido chega ao prompt de sumarização (o 1º prompt gerado)
    assert 'novo artigo é: "tesouraria"' in prompts[0]
    # a palavra_chave de SEO do LLM é distinta do ângulo do catálogo
    assert post["palavra_chave"] == "conciliação bancária da igreja"
    assert (tmp_path / "post.json").exists()


def test_gerar_post_blog_tenta_proximo_angulo_quando_um_falha(monkeypatch, tmp_path):
    # Um artigo casa "imunidade tributária" (score 12) e "tesouraria" (score 3): imunidade é
    # escolhida primeiro. A 1ª geração devolve JSON inválido → deve cair para o próximo ângulo.
    corpus = [{
        "url": "a", "titulo": "t",
        "corpo": "imunidade tributária imunidade tributária tesouraria", "peso": 3, "data": None,
    }]
    chamadas = {"n": 0}

    def fake_gerar(prompt):
        chamadas["n"] += 1
        if chamadas["n"] % 2 == 1:  # chamadas ímpares = sumarização
            return "ctx"
        # 1ª geração de artigo (chamada 2) inválida; 2ª (chamada 4) válida
        return json.dumps({"titulo": "só título"}) if chamadas["n"] == 2 else json.dumps(_dados_validos())

    monkeypatch.setattr(artigo, "gerar", fake_gerar)
    monkeypatch.setattr(artigo, "POST_BLOG_PATH", tmp_path / "post.json")
    monkeypatch.setattr(artigo, "ARTIGO_PATH", tmp_path / "artigo.md")

    _, eixo, angulo = artigo.gerar_post_blog(corpus, [], PALAVRAS, {}, cooldown_posts=3)

    assert angulo == "tesouraria"  # imunidade tributária foi descartada após a falha
    assert eixo == "rotina-financeira"
