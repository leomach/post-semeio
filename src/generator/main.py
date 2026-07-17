"""Entrypoint do Módulo 2+3 — Geração de artigo e carrossel."""
import json
import logging
import sys

from src.config import CONTEUDO_EXTRAIDO_PATH, TEMA_COOLDOWN_POSTS
from src.generator.artigo import gerar_post_blog, markdown_do_post
from src.generator.carrossel import gerar_carrossel
from src.scraper import dedup
from src.scraper.fontes import carregar_fontes

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

    estado = dedup.carregar_estado()
    palavras_chave = carregar_fontes().palavras_chave

    try:
        post, eixo = gerar_post_blog(artigos_extraidos, palavras_chave, estado, TEMA_COOLDOWN_POSTS)
        gerar_carrossel(markdown_do_post(post))
    except Exception:
        logger.error("Falha na geração de conteúdo — pipeline interrompido antes do envio ao Telegram", exc_info=True)
        return 1

    # Só registra o eixo no histórico após artigo E carrossel gerados com sucesso, para que o
    # cooldown só avance quando de fato houve publicação.
    dedup.registrar_post_publicado(estado, eixo, post["palavra_chave"], post["titulo"])
    dedup.salvar_estado(estado)

    logger.info("Post de blog e carrossel gerados com sucesso (eixo '%s')", eixo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
