"""Entrypoint do Módulo 5 — Notificação via Telegram.

Com a publicação automática (Módulo 4) bem-sucedida, manda só o link do post e o carrossel.
Sem ela (``publicacao.json`` ausente), manda o post completo para publicação manual.
"""
import json
import logging
import sys

from src.config import CARROSSEL_PATH, POST_BLOG_PATH, PUBLICACAO_PATH
from src.notifier.telegram import enviar_carrossel, enviar_post_blog, enviar_publicacao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# NFR 6.4: o token do bot vai embutido na própria URL da API do Telegram
# (/bot<TOKEN>/sendMessage) — o logger INFO do httpx logaria a URL completa a cada
# requisição, vazando o token em texto puro nos logs. Suprimimos esse nível aqui.
logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> int:
    if not POST_BLOG_PATH.exists() or not CARROSSEL_PATH.exists():
        logger.info("Nenhum post/carrossel gerado neste ciclo — nada a notificar")
        return 0

    with open(POST_BLOG_PATH, "r", encoding="utf-8") as f:
        post = json.load(f)
    with open(CARROSSEL_PATH, "r", encoding="utf-8") as f:
        carrossel = json.load(f)

    publicacao = None
    if PUBLICACAO_PATH.exists():
        with open(PUBLICACAO_PATH, "r", encoding="utf-8") as f:
            publicacao = json.load(f)

    try:
        if publicacao is not None:
            enviar_publicacao(post, publicacao)
        else:
            enviar_post_blog(post, falha_publicacao=True)
        enviar_carrossel(carrossel)
    except Exception:
        logger.error("Falha ao enviar mensagens ao Telegram", exc_info=True)
        return 1

    logger.info("Mensagens enviadas ao Telegram com sucesso")
    return 0


if __name__ == "__main__":
    sys.exit(main())
