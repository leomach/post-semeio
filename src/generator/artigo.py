"""Orquestra sumarização + geração do post de blog SEO (RF05-RF09 + checklist de SEO)."""
import json
import logging
import re
import unicodedata

from src.config import (
    ARTIGO_MIN_SUBTITULOS,
    ARTIGO_PATH,
    BLOG_CONTEUDO_MIN_PALAVRAS,
    BLOG_LINKS_INTERNOS,
    BLOG_MIN_TAGS,
    BLOG_RESUMO_IDEAL_MAX,
    BLOG_RESUMO_IDEAL_MIN,
    BLOG_RESUMO_MAX,
    BLOG_SEO_TITULO_IDEAL_MAX,
    BLOG_SLUG_MAX,
    POST_BLOG_PATH,
)
from src.generator.json_util import limpar_json
from src.generator.llm_client import gerar
from src.generator.prompts.artigo import montar_prompt_artigo
from src.generator.prompts.sumarizacao import montar_prompt_sumarizacao

logger = logging.getLogger(__name__)


def _artigos_do_tema_mais_relevante(artigos_extraidos: list[dict]) -> list[dict]:
    """RF05: agrupa apenas o conteúdo relacionado ao tema de maior peso do ciclo atual."""
    maior_peso = max(artigo["peso"] for artigo in artigos_extraidos)
    return [artigo for artigo in artigos_extraidos if artigo["peso"] == maior_peso]


def slugify(texto: str, max_chars: int = BLOG_SLUG_MAX) -> str:
    """Normaliza para slug: sem acentos, minúsculo, hífens; truncado em fronteira de palavra."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    if len(texto) <= max_chars:
        return texto
    cortado = texto[:max_chars].rsplit("-", 1)[0]
    return cortado or texto[:max_chars]


def _niveis_headings(conteudo: str) -> list[int]:
    return [len(m.group(1)) for m in re.finditer(r"^(#{1,6})\s", conteudo, re.MULTILINE)]


def _primeiro_paragrafo(conteudo: str) -> str:
    for bloco in conteudo.split("\n\n"):
        bloco = bloco.strip()
        if bloco and not bloco.startswith("#"):
            return bloco
    return ""


def _validar_post(post: dict) -> None:
    """Validações estruturais (hard fail) + checagens de SEO (warning). Human-in-the-loop
    revisa no Telegram antes de publicar, então critérios "ideais" apenas avisam."""
    palavra_chave = post.get("palavra_chave", "").lower()
    conteudo = post["conteudo"]

    # --- Campos obrigatórios não vazios ---
    for campo in ("titulo", "slug", "resumo", "conteudo", "capa_alt"):
        if not str(post.get(campo, "")).strip():
            raise ValueError(f"Campo obrigatório '{campo}' está vazio no post gerado")

    # --- Resumo (hard: <= 280; soft: 150-160) ---
    if len(post["resumo"]) > BLOG_RESUMO_MAX:
        raise ValueError(f"Resumo excede {BLOG_RESUMO_MAX} caracteres ({len(post['resumo'])})")
    if not (BLOG_RESUMO_IDEAL_MIN <= len(post["resumo"]) <= BLOG_RESUMO_IDEAL_MAX):
        logger.warning(
            "Resumo com %d chars fora do ideal (%d-%d)",
            len(post["resumo"]), BLOG_RESUMO_IDEAL_MIN, BLOG_RESUMO_IDEAL_MAX,
        )

    # --- Estrutura de headings ---
    niveis = _niveis_headings(conteudo)
    if any(n == 1 for n in niveis):
        raise ValueError("Conteúdo contém H1 (`# `) — o H1 é reservado ao título do post")
    if sum(1 for n in niveis if n == 2) < ARTIGO_MIN_SUBTITULOS:
        raise ValueError(f"Conteúdo tem menos de {ARTIGO_MIN_SUBTITULOS} seções `## ` (H2)")
    anterior = 1
    for n in niveis:
        if n > anterior + 1:
            raise ValueError(f"Salto de heading inválido: H{anterior} → H{n} (nunca pule níveis)")
        anterior = n

    # --- Profundidade ---
    n_palavras = len(conteudo.split())
    if n_palavras < BLOG_CONTEUDO_MIN_PALAVRAS:
        raise ValueError(
            f"Conteúdo com {n_palavras} palavras, mínimo é {BLOG_CONTEUDO_MIN_PALAVRAS}"
        )

    # --- Links internos ---
    if not any(link in conteudo for link in BLOG_LINKS_INTERNOS):
        raise ValueError(
            f"Conteúdo não contém link interno para páginas do produto {BLOG_LINKS_INTERNOS}"
        )

    # --- Tags ---
    tags = post.get("tags") or []
    if not isinstance(tags, list) or len(tags) < BLOG_MIN_TAGS:
        raise ValueError(f"Post deve ter ao menos {BLOG_MIN_TAGS} tags")

    # --- Palavra-chave nos lugares-chave (soft: warning) ---
    if palavra_chave:
        if palavra_chave not in post["titulo"].lower():
            logger.warning("Palavra-chave '%s' ausente do título", palavra_chave)
        if palavra_chave not in post["resumo"].lower():
            logger.warning("Palavra-chave '%s' ausente do resumo", palavra_chave)
        if palavra_chave not in _primeiro_paragrafo(conteudo).lower():
            logger.warning("Palavra-chave '%s' ausente do primeiro parágrafo", palavra_chave)
        if palavra_chave and not any(t in post["slug"] for t in slugify(palavra_chave).split("-")):
            logger.warning("Palavra-chave '%s' ausente do slug", palavra_chave)

    # --- SEO título (soft) ---
    seo_titulo = post.get("seo_titulo", "")
    if seo_titulo and len(seo_titulo) > BLOG_SEO_TITULO_IDEAL_MAX:
        logger.warning("seo_titulo com %d chars acima do ideal (%d)", len(seo_titulo), BLOG_SEO_TITULO_IDEAL_MAX)


def _montar_post(dados: dict) -> dict:
    """Normaliza os campos vindos do LLM: slug reslugificado, status e defaults."""
    titulo = str(dados.get("titulo", "")).strip()
    slug = slugify(dados.get("slug") or titulo)
    resumo = str(dados.get("resumo", "")).strip()
    return {
        "palavra_chave": str(dados.get("palavra_chave", "")).strip(),
        "titulo": titulo,
        "slug": slug,
        "resumo": resumo,
        "conteudo": str(dados.get("conteudo", "")).strip(),
        "capa_url": dados.get("capa_url", ""),
        "capa_alt": str(dados.get("capa_alt", "")).strip(),
        "seo_titulo": str(dados.get("seo_titulo", "")).strip(),
        "seo_descricao": str(dados.get("seo_descricao", "")).strip() or resumo,
        "tags": [str(t).strip() for t in (dados.get("tags") or []) if str(t).strip()],
        "status": "Publicado",
    }


def gerar_post_blog(artigos_extraidos: list[dict]) -> dict:
    artigos_relevantes = _artigos_do_tema_mais_relevante(artigos_extraidos)
    prompt_sumarizacao = montar_prompt_sumarizacao(artigos_relevantes)
    contexto_unificado = gerar(prompt_sumarizacao)

    prompt_artigo = montar_prompt_artigo(contexto_unificado)
    resposta = gerar(prompt_artigo)

    try:
        dados = json.loads(limpar_json(resposta))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resposta do LLM não é JSON válido: {exc}") from exc

    post = _montar_post(dados)
    _validar_post(post)

    POST_BLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(POST_BLOG_PATH, "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)

    # artigo.md: versão legível/renderizável (título como H1 + conteúdo em H2+), usada como
    # base para o carrossel e mantida por compatibilidade com o critério de aceite do Módulo 2.
    with open(ARTIGO_PATH, "w", encoding="utf-8") as f:
        f.write(f"# {post['titulo']}\n\n{post['conteudo']}\n")

    return post


def markdown_do_post(post: dict) -> str:
    return f"# {post['titulo']}\n\n{post['conteudo']}"
