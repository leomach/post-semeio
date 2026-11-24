"""Publicação do post no blog do Semeio pela API de integração do Django.

    POST {SEMEIO_API_URL}
    Authorization: Bearer {SEMEIO_BLOG_TOKEN}

Contrato: docs/guia-desenvolvedor/api-site.md, seção 5, no repositório DinDin.
"""
import os

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import (
    BLOG_MAX_TAGS,
    BLOG_SEO_DESCRICAO_MAX,
    BLOG_SEO_TITULO_MAX,
    BLOG_STATUS,
    BLOG_TAG_MAX_CHARS,
    BLOG_TITULO_MAX,
    HTTP_TIMEOUT_SECONDS,
    MAX_RETRIES,
    SEMEIO_API_URL,
)

STATUS_VALIDOS = ("publicado", "rascunho")


class PublicacaoRecusada(RuntimeError):
    """A API recusou o post (4xx): não adianta repetir, o conteúdo precisa mudar."""


def _token() -> str:
    token = os.environ.get("SEMEIO_BLOG_TOKEN")
    if not token:
        raise RuntimeError("SEMEIO_BLOG_TOKEN não configurado no ambiente")
    return token


def montar_payload(post: dict, status: str = BLOG_STATUS) -> dict:
    """Converte o post gerado no corpo da API, respeitando os limites do model no Django.

    Campos opcionais acima do limite são omitidos em vez de truncados: um título de SEO cortado
    no meio é pior que o título do post, que o site usa quando o de SEO falta.
    """
    if status not in STATUS_VALIDOS:
        raise ValueError(f"BLOG_STATUS deve ser um de {STATUS_VALIDOS}, recebido: {status!r}")

    payload = {
        "titulo": post["titulo"][:BLOG_TITULO_MAX],
        "slug": post["slug"],
        "resumo": post["resumo"],
        "conteudo": post["conteudo"],
        "status": status,
        "tags": [t for t in post.get("tags", []) if len(t) <= BLOG_TAG_MAX_CHARS][:BLOG_MAX_TAGS],
    }
    opcionais = {
        "seo_titulo": BLOG_SEO_TITULO_MAX,
        "seo_descricao": BLOG_SEO_DESCRICAO_MAX,
        "capa_alt": 180,
    }
    for campo, limite in opcionais.items():
        valor = (post.get(campo) or "").strip()
        if valor and len(valor) <= limite:
            payload[campo] = valor
    capa_url = (post.get("capa_url") or "").strip()
    if capa_url.startswith(("http://", "https://")):
        payload["capa_url"] = capa_url
    return payload


def _deve_repetir(exc: BaseException) -> bool:
    # Rede e 5xx são transitórios; 4xx (validação, token) não mudam com nova tentativa.
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception(_deve_repetir),
    reraise=True,
)
def _postar(payload: dict, token: str) -> httpx.Response:
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resposta = client.post(
            SEMEIO_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    if resposta.status_code >= 500:
        resposta.raise_for_status()
    return resposta


def publicar_post(post: dict, status: str = BLOG_STATUS) -> dict:
    """Cria o post no blog. Devolve a resposta da API, com ``ja_existia`` indicando reenvio.

    Slug repetido (409) não é erro: o mesmo post já foi publicado num ciclo anterior (reenvio
    após falha no fim do pipeline), e a API devolve o post existente.
    """
    resposta = _postar(montar_payload(post, status), _token())

    if resposta.status_code == 201:
        return {**resposta.json(), "ja_existia": False}
    if resposta.status_code == 409:
        corpo = resposta.json()
        return {"id": corpo.get("id"), "slug": post["slug"], "url": corpo.get("url"),
                "admin_url": corpo.get("admin_url"), "status": status, "ja_existia": True}

    # Resposta da Cloudflare (403 com HTML) não tem JSON: mostra o começo do corpo.
    try:
        detalhe = resposta.json()
    except ValueError:
        detalhe = resposta.text[:300]
    raise PublicacaoRecusada(f"API do Semeio respondeu {resposta.status_code}: {detalhe}")
