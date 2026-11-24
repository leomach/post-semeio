"""Entrypoint do Módulo 4 — Publicação do post no blog do Semeio."""
import json
import logging
import sys

from src.config import BLOG_STATUS, POST_BLOG_PATH, PUBLICACAO_PATH
from src.publisher.semeio_api import publicar_post

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    if not POST_BLOG_PATH.exists():
        logger.info("Nenhum post gerado neste ciclo — nada a publicar")
        return 0

    with open(POST_BLOG_PATH, "r", encoding="utf-8") as f:
        post = json.load(f)

    try:
        resultado = publicar_post(post)
    except Exception:
        # Sem publicacao.json, o notificador manda o post completo ao Telegram (fallback
        # manual), então o conteúdo gerado não se perde.
        logger.error("Falha ao publicar o post no blog do Semeio", exc_info=True)
        return 1

    PUBLICACAO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PUBLICACAO_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    if resultado["ja_existia"]:
        logger.info("Post já existia no blog (slug %s): %s", post["slug"], resultado["url"])
    else:
        logger.info("Post criado no blog como %s: %s", BLOG_STATUS, resultado["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
