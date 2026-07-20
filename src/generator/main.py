"""Entrypoint do Módulo 2+3 — Geração de artigo e carrossel."""
import json
import logging
import sys

from src.config import CONTEUDO_EXTRAIDO_PATH, TEMA_COOLDOWN_POSTS
from src.generator.artigo import gerar_post_blog, markdown_do_post
from src.generator.carrossel import gerar_carrossel
from src.scraper import corpus as corpus_mod
from src.scraper import dedup
from src.scraper.fontes import carregar_fontes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _carregar_frescos() -> list[dict]:
    """Lote de artigos extraídos NESTE ciclo (preferidos na escolha do ângulo). Ausência do
    arquivo/erro de leitura não é fatal — o corpus persistido cobre a geração."""
    if not CONTEUDO_EXTRAIDO_PATH.exists():
        return []
    try:
        with open(CONTEUDO_EXTRAIDO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def main() -> int:
    frescos = _carregar_frescos()
    corpus_artigos = corpus_mod.artigos(corpus_mod.carregar_corpus())

    # Só não há o que gerar quando NÃO há material fresco E o corpus está vazio. Enquanto o
    # corpus tiver artigos, sempre existe um ângulo (subtema) a explorar — mesmo sem novidade.
    if not frescos and not corpus_artigos:
        logger.info("Sem material fresco e corpus vazio — nada a gerar neste ciclo")
        return 0

    estado = dedup.carregar_estado()
    palavras_chave = carregar_fontes().palavras_chave

    try:
        post, eixo, angulo = gerar_post_blog(
            corpus_artigos, frescos, palavras_chave, estado, TEMA_COOLDOWN_POSTS
        )
        gerar_carrossel(markdown_do_post(post))
    except Exception:
        logger.error("Falha na geração de conteúdo — pipeline interrompido antes do envio ao Telegram", exc_info=True)
        return 1

    # Só registra o ângulo/eixo no histórico após artigo E carrossel gerados com sucesso, para
    # que o cooldown de eixo e a rotação de ângulo só avancem quando de fato houve publicação.
    dedup.registrar_post_publicado(estado, eixo, angulo, post["palavra_chave"], post["titulo"])
    dedup.salvar_estado(estado)

    logger.info(
        "Post de blog e carrossel gerados com sucesso (eixo '%s', ângulo '%s')", eixo, angulo
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
