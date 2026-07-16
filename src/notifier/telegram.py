"""Integração com a API do Telegram (RF13-RF16)."""
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import HTTP_TIMEOUT_SECONDS, MAX_RETRIES, TELEGRAM_API_BASE, TELEGRAM_MAX_MENSAGEM

CABECALHO_ARTIGO = "📄 POST PARA O BLOG"
CABECALHO_CONTEUDO = "📝 CONTEÚDO (Markdown)"
CABECALHO_CARROSSEL = "📱 ROTEIRO PARA INSTAGRAM"


def _credenciais() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não configurados no ambiente")
    return token, chat_id


def dividir_mensagem(texto: str, limite: int = TELEGRAM_MAX_MENSAGEM) -> list[str]:
    """Divide texto em pedaços <= limite, preferindo cortar em quebras de parágrafo/linha."""
    if len(texto) <= limite:
        return [texto]

    partes: list[str] = []
    restante = texto
    while len(restante) > limite:
        corte = restante.rfind("\n\n", 0, limite)
        if corte == -1:
            corte = restante.rfind("\n", 0, limite)
        if corte == -1:
            corte = limite
        partes.append(restante[:corte].rstrip())
        restante = restante[corte:].lstrip("\n")
    if restante:
        partes.append(restante)
    return partes


def _enviar(texto: str) -> None:
    token, chat_id = _credenciais()
    _postar_mensagem(token, chat_id, texto)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _postar_mensagem(token: str, chat_id: str, texto: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resposta = client.post(url, json={"chat_id": chat_id, "text": texto})
        resposta.raise_for_status()
        corpo = resposta.json()
        if not corpo.get("ok"):
            raise RuntimeError(f"Telegram API retornou erro: {corpo}")


def _formatar_metadados_post(post: dict) -> str:
    """Bloco com os campos que o usuário copia para o formulário do blog (RF14/RF16)."""
    tags = ", ".join(post.get("tags", []))
    linhas = [
        CABECALHO_ARTIGO,
        "",
        f"📌 TÍTULO\n{post.get('titulo', '')}",
        f"🔗 SLUG\n{post.get('slug', '')}",
        f"📝 RESUMO (meta description)\n{post.get('resumo', '')}",
        f"🏷️ TAGS\n{tags}",
        f"🔎 SEO TÍTULO\n{post.get('seo_titulo', '')}",
        f"🔎 SEO DESCRIÇÃO\n{post.get('seo_descricao', '')}",
        f"🖼️ CAPA ALT\n{post.get('capa_alt', '')}",
        f"✅ STATUS\n{post.get('status', '')}",
    ]
    return "\n\n".join(linhas)


def enviar_post_blog(post: dict) -> None:
    """Envia os metadados do post e, em seguida, o conteúdo Markdown (RF14/RF16)."""
    _enviar(_formatar_metadados_post(post))
    _enviar(CABECALHO_CONTEUDO)
    for pedaco in dividir_mensagem(post.get("conteudo", "")):
        _enviar(pedaco)


def _formatar_carrossel(dados: dict) -> str:
    linhas = []
    for slide in sorted(dados.get("slides", []), key=lambda s: s.get("ordem", 0)):
        linhas.append(f"[{slide.get('ordem')}] ({slide.get('tipo')}) {slide.get('texto')}")

    legenda = dados.get("legenda", "")
    hashtags = " ".join(dados.get("hashtags", []))

    return (
        "\n\n".join(linhas)
        + "\n\n--- Legenda ---\n"
        + legenda
        + ("\n\n" + hashtags if hashtags else "")
    )


def enviar_carrossel(dados: dict) -> None:
    _enviar(CABECALHO_CARROSSEL)
    texto = _formatar_carrossel(dados)
    for pedaco in dividir_mensagem(texto):
        _enviar(pedaco)
