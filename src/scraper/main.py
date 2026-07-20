"""Entrypoint do Módulo 1 — Pesquisa e Extração de Conteúdo."""
import json
import logging

from src.config import (
    CIRCUIT_BREAKER_FALHAS_CONSECUTIVAS,
    CONTEUDO_EXTRAIDO_PATH,
    CORPUS_MAX_ARTIGOS,
    OUTPUT_DIR,
)
from src.scraper import corpus as corpus_mod
from src.scraper import dedup
from src.scraper.extrator import processar_fonte
from src.scraper.fontes import carregar_fontes, fontes_ativas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    config = carregar_fontes()
    ativas = fontes_ativas(config)
    estado = dedup.carregar_estado()
    corpus = corpus_mod.carregar_corpus()

    todos_artigos: list[dict] = []

    for fonte in ativas:
        logger.info("Processando fonte: %s", fonte.nome)
        # Gate por "já está no corpus" (não por links_processados): assim, URLs antigas cujo
        # corpo foi descartado antes da introdução do corpus são re-extraídas e reabastecidas
        # naturalmente (auto-backfill), enquanto o que já está no corpus não é re-baixado.
        artigos = processar_fonte(
            fonte,
            config.palavras_chave,
            ja_processado_fn=lambda url: corpus_mod.em_corpus(url, corpus),
            max_falhas_consecutivas=CIRCUIT_BREAKER_FALHAS_CONSECUTIVAS,
        )
        for artigo in artigos:
            dedup.registrar_processado(artigo["url"], artigo["fonte"], artigo["titulo"], estado)
            corpus_mod.registrar_artigo(corpus, artigo)
        todos_artigos.extend(artigos)
        logger.info("Fonte %s: %d artigo(s) novo(s) extraído(s)", fonte.nome, len(artigos))

    todos_artigos.sort(key=lambda a: a["peso"], reverse=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONTEUDO_EXTRAIDO_PATH, "w", encoding="utf-8") as f:
        json.dump(todos_artigos, f, ensure_ascii=False, indent=2)

    removidos = corpus_mod.podar_corpus(corpus, CORPUS_MAX_ARTIGOS)
    corpus_mod.salvar_corpus(corpus)
    dedup.salvar_estado(estado)

    logger.info(
        "Total de artigos novos extraídos no ciclo: %d | corpus: %d artigo(s) (%d podado(s))",
        len(todos_artigos),
        len(corpus.get("artigos", {})),
        removidos,
    )


if __name__ == "__main__":
    main()
