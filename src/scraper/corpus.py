"""Corpus persistente de artigos extraídos.

Diferente de ``links_processados`` (que guarda apenas o hash da URL, para não re-baixar a mesma
página), o corpus guarda o CORPO completo de cada artigo, acumulado ao longo dos ciclos e
versionado no git. É o que permite ao gerador produzir posts sobre subtemas diferentes a partir
do mesmo material mesmo em ciclos sem nenhum artigo novo.

Chaveamento pelo mesmo hash de URL normalizada usado em ``dedup``, de modo que uma URL vista de
formas equivalentes (com/sem barra final, com tracking params) mapeia para uma única entrada.
"""
import json
from datetime import datetime, timezone

from src.config import CORPUS_PATH
from src.scraper.dedup import calcular_hash, normalizar_url


def carregar_corpus() -> dict:
    if not CORPUS_PATH.exists():
        return {"artigos": {}}
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_corpus(corpus: dict) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
        f.write("\n")


def em_corpus(url: str, corpus: dict) -> bool:
    return calcular_hash(normalizar_url(url)) in corpus.get("artigos", {})


def registrar_artigo(corpus: dict, artigo: dict) -> str:
    """Upsert de um artigo no corpus, chaveado pelo hash da URL normalizada.

    Ao reencontrar uma URL já existente, preserva ``adicionado_em`` (para a poda por antiguidade
    permanecer estável) e mantém o maior ``peso`` já visto, atualizando título/corpo/data com o
    conteúdo mais recente.
    """
    artigos = corpus.setdefault("artigos", {})
    url = artigo["url"]
    hash_url = calcular_hash(normalizar_url(url))
    existente = artigos.get(hash_url)

    adicionado_em = existente["adicionado_em"] if existente else datetime.now(timezone.utc).isoformat()
    peso = artigo.get("peso", 0)
    if existente:
        peso = max(peso, existente.get("peso", 0))

    artigos[hash_url] = {
        "url": url,
        "fonte": artigo.get("fonte", ""),
        "titulo": artigo.get("titulo", ""),
        "corpo": artigo.get("corpo", ""),
        "data": artigo.get("data"),
        "peso": peso,
        "adicionado_em": adicionado_em,
    }
    return hash_url


def podar_corpus(corpus: dict, max_artigos: int) -> int:
    """Mantém no máximo ``max_artigos`` entradas, descartando as mais antigas primeiro.

    Ordem determinística: ``(adicionado_em, hash)``. Devolve quantas entradas foram removidas.
    """
    artigos = corpus.get("artigos", {})
    excedente = len(artigos) - max_artigos
    if excedente <= 0:
        return 0

    ordenados = sorted(artigos.items(), key=lambda item: (item[1].get("adicionado_em") or "", item[0]))
    for hash_url, _ in ordenados[:excedente]:
        del artigos[hash_url]
    return excedente


def artigos(corpus: dict) -> list[dict]:
    return list(corpus.get("artigos", {}).values())
