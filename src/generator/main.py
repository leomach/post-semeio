"""Entrypoint do Módulo 2+3 — Geração de artigo e carrossel."""
import json
import logging
import sys

from src.config import CONTEUDO_EXTRAIDO_PATH
from src.generator.artigo import gerar_post_blog, markdown_do_post
from src.generator.carrossel import gerar_carrossel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    if not CONTEUDO_EXTRAIDO_PATH.exists():
        logger.error("Nenhum conteúdo extraído encontrado em %s — rode o scraper antes", CONTEUDO_EXTRAIDO_PATH)
        return 1

    with open(CONTEUDO_EXTRAIDO_PATH, "r", encoding="utf-8") as f:
        artigos_extraidos = json.load(f)

    if not artigos_extraidos:
        logger.info("Nenhum artigo novo neste ciclo — nada a gerar")
        return 0

    try:
        post = gerar_post_blog(artigos_extraidos)
        gerar_carrossel(markdown_do_post(post))
    except Exception:
        logger.error("Falha na geração de conteúdo — pipeline interrompido antes do envio ao Telegram", exc_info=True)
        return 1

    logger.info("Post de blog e carrossel gerados com sucesso")
    return 0


if __name__ == "__main__":
    sys.exit(main())
