"""Seleção da pauta-base com diversidade temática.

Substitui a antiga regra "pega o artigo de maior peso" por uma escolha que respeita um cooldown
por eixo temático: um eixo publicado nos últimos N posts (ver TEMA_COOLDOWN_POSTS) é evitado, de
modo que assuntos parecidos não se repitam em posts seguidos. Se todos os eixos disponíveis no
ciclo estiverem em cooldown, escolhe o menos recente para não travar o pipeline.
"""
import logging

from src.scraper.dedup import eixos_recentes
from src.scraper.fontes import PalavraChave

logger = logging.getLogger(__name__)

EIXO_PADRAO = "geral"


def classificar_eixo(artigo: dict, palavras_chave: list[PalavraChave]) -> str:
    """Eixo dominante do artigo: soma o peso das palavras-chave presentes no título+corpo,
    agrupando por eixo, e retorna o eixo de maior peso acumulado."""
    texto = f"{artigo.get('titulo', '')} {artigo.get('corpo', '')}".lower()
    peso_por_eixo: dict[str, int] = {}
    for pc in palavras_chave:
        if pc.termo.lower() in texto:
            peso_por_eixo[pc.eixo] = peso_por_eixo.get(pc.eixo, 0) + pc.peso
    if not peso_por_eixo:
        return EIXO_PADRAO
    # Desempate estável por nome do eixo, para escolha determinística.
    return max(peso_por_eixo.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _ordenar_artigos(artigos: list[dict]) -> list[dict]:
    """Do mais relevante para o menos: maior peso e, em empate, mais recente."""
    return sorted(artigos, key=lambda a: (a.get("peso", 0), a.get("data") or ""), reverse=True)


def selecionar_pauta(
    artigos: list[dict],
    palavras_chave: list[PalavraChave],
    estado: dict,
    cooldown_posts: int,
) -> tuple[str, list[dict]]:
    """Escolhe o eixo da próxima pauta respeitando o cooldown e devolve
    ``(eixo, artigos_do_eixo)``. Os artigos do eixo (ordenados por relevância) servem de
    contexto para a sumarização. Anota ``eixo`` em cada artigo de entrada.

    Levanta ``ValueError`` se ``artigos`` estiver vazio.
    """
    if not artigos:
        raise ValueError("Nenhum artigo disponível para selecionar a pauta")

    for artigo in artigos:
        artigo["eixo"] = classificar_eixo(artigo, palavras_chave)

    grupos: dict[str, list[dict]] = {}
    for artigo in artigos:
        grupos.setdefault(artigo["eixo"], []).append(artigo)

    def score(eixo: str) -> int:
        return max(a.get("peso", 0) for a in grupos[eixo])

    em_cooldown = eixos_recentes(estado, cooldown_posts)
    ja_publicados = {p.get("eixo") for p in estado.get("historico_posts", [])}
    elegiveis = [eixo for eixo in grupos if eixo not in em_cooldown]

    if elegiveis:
        # Prioriza eixos nunca publicados, depois maior peso; desempate estável pelo nome.
        eixo_escolhido = max(
            elegiveis,
            key=lambda eixo: (eixo not in ja_publicados, score(eixo), eixo),
        )
    else:
        # Todos os eixos do ciclo estão em cooldown: reaproveita o publicado há mais tempo.
        # `em_cooldown` está em ordem cronológica (mais antigo primeiro); a posição da ÚLTIMA
        # ocorrência de cada eixo indica há quanto tempo foi publicado pela última vez.
        ultima_posicao = {eixo: i for i, eixo in enumerate(em_cooldown)}
        eixo_escolhido = min(grupos, key=lambda eixo: (ultima_posicao.get(eixo, len(em_cooldown)), eixo))
        logger.warning(
            "Todos os eixos deste ciclo estão em cooldown (%s) — reaproveitando o menos recente: '%s'",
            ", ".join(dict.fromkeys(em_cooldown)),
            eixo_escolhido,
        )

    artigos_do_eixo = _ordenar_artigos(grupos[eixo_escolhido])
    logger.info(
        "Eixo escolhido: '%s' (%d artigo(s), cooldown atual: %s)",
        eixo_escolhido,
        len(artigos_do_eixo),
        ", ".join(dict.fromkeys(em_cooldown)) or "vazio",
    )
    return eixo_escolhido, artigos_do_eixo
