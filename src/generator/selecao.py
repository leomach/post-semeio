"""Seleção da pauta por ÂNGULO (subtema) com diversidade temática.

A pauta de cada ciclo é um *ângulo* — uma palavra-chave do catálogo (``PalavraChave.termo``) que
tem lastro no material disponível. Isso permite gerar posts sobre assuntos diferentes a partir do
mesmo corpus de artigos: o mesmo artigo-fonte sustenta vários ângulos ao longo do tempo.

Regras de escolha (determinísticas, para o pipeline ser reprodutível dado o estado commitado):
- **Prefere material fresco**: se o ciclo trouxe artigos novos que sustentam algum ângulo
  elegível, escolhe entre eles; senão cai no corpus inteiro.
- **Cooldown de eixo**: um eixo publicado nos últimos N posts (``TEMA_COOLDOWN_POSTS``) é evitado.
- **Rotação de ângulo**: prioriza ângulos nunca publicados; entre os já publicados, o menos
  recente (LRU). Desempate por maior lastro (score) e, por fim, nome do termo.
- **Garantia**: havendo qualquer material (fresco ou corpus) que case ao menos um termo, sempre
  há um ângulo — nunca "nada a gerar". Se todos os eixos estiverem em cooldown, o cooldown é
  relaxado (com aviso) em vez de travar.

A função é pura: não muta os dicts de entrada (essencial, pois eles vêm do corpus persistido).
"""
import logging

from src.config import ANGULO_MAX_CHARS_CONTEXTO, ANGULO_MIN_SUPORTE, ANGULO_TOP_K_ARTIGOS
from src.scraper.dedup import angulos_publicados, eixos_recentes
from src.scraper.fontes import PalavraChave

logger = logging.getLogger(__name__)


def _texto(artigo: dict) -> str:
    return f"{artigo.get('titulo', '')} {artigo.get('corpo', '')}".lower()


def _mapa_suporte(artigos: list[dict], palavras_chave: list[PalavraChave]) -> dict:
    """termo -> {"pc": PalavraChave, "artigos": [(score, artigo), ...]}.

    ``score`` do artigo para o ângulo = nº de ocorrências do termo × peso do termo — um lastro
    específico do ângulo (melhor que o ``peso`` bruto do artigo, que soma toda a âncora)."""
    textos = [(a, _texto(a)) for a in artigos]
    mapa: dict = {}
    for pc in palavras_chave:
        termo = pc.termo.lower()
        suportes = [(texto.count(termo) * pc.peso, a) for a, texto in textos if termo in texto]
        if suportes:
            mapa[pc.termo] = {"pc": pc, "artigos": suportes}
    return mapa


def _elegiveis(mapa: dict, em_cooldown: set, excluir: frozenset, min_suporte: int) -> list[str]:
    return [
        termo
        for termo, info in mapa.items()
        if termo not in excluir
        and len(info["artigos"]) >= min_suporte
        and info["pc"].eixo not in em_cooldown
    ]


def _artigos_suporte(suportes: list, top_k: int, max_chars: int) -> list[dict]:
    """Ordena o suporte por relevância (score, peso, url) e devolve o top-K sob o teto de chars.
    Sempre inclui ao menos um artigo."""
    ordenados = sorted(
        suportes,
        key=lambda par: (-par[0], -par[1].get("peso", 0), par[1].get("url", "")),
    )
    selecionados: list[dict] = []
    total = 0
    for _score, artigo in ordenados[:top_k]:
        corpo_len = len(artigo.get("corpo", ""))
        if selecionados and total + corpo_len > max_chars:
            break
        selecionados.append(artigo)
        total += corpo_len
    return selecionados


def selecionar_angulo(
    corpus_artigos: list[dict],
    palavras_chave: list[PalavraChave],
    estado: dict,
    cooldown_posts: int,
    fresh_artigos: list[dict] | None = None,
    min_suporte: int = ANGULO_MIN_SUPORTE,
    top_k: int = ANGULO_TOP_K_ARTIGOS,
    max_chars: int = ANGULO_MAX_CHARS_CONTEXTO,
    excluir_angulos: frozenset = frozenset(),
) -> tuple[str, str, list[dict]]:
    """Escolhe o ângulo da próxima pauta e devolve ``(eixo, angulo, artigos_suporte)``.

    Levanta ``ValueError`` se não houver nenhum material que sustente qualquer ângulo elegível
    (corpus e fresco vazios, ou sem casar termo algum fora de ``excluir_angulos``)."""
    fresh_map = _mapa_suporte(fresh_artigos or [], palavras_chave)
    corpus_map = _mapa_suporte(corpus_artigos, palavras_chave)
    em_cooldown = set(eixos_recentes(estado, cooldown_posts))

    # Ordem de tentativa: fresco→corpus com cooldown; depois fresco→corpus relaxando o cooldown.
    tentativas = [
        (fresh_map, em_cooldown, "fresco", False),
        (corpus_map, em_cooldown, "corpus", False),
        (fresh_map, set(), "fresco", True),
        (corpus_map, set(), "corpus", True),
    ]
    mapa: dict = {}
    elegiveis: list[str] = []
    origem = ""
    relaxado = False
    for candidato_mapa, cooldown, nome_origem, eh_relaxado in tentativas:
        candidatos = _elegiveis(candidato_mapa, cooldown, excluir_angulos, min_suporte)
        if candidatos:
            mapa, elegiveis, origem, relaxado = candidato_mapa, candidatos, nome_origem, eh_relaxado
            break

    if not elegiveis:
        raise ValueError("Nenhum ângulo com lastro disponível (corpus e material fresco vazios)")

    if relaxado:
        logger.warning(
            "Todos os eixos com material estão em cooldown (%s) — relaxando o cooldown para não travar",
            ", ".join(dict.fromkeys(eixos_recentes(estado, cooldown_posts))) or "vazio",
        )

    publicados = angulos_publicados(estado)
    publicados_set = set(publicados)
    ultima_posicao = {angulo: i for i, angulo in enumerate(publicados)}

    def score_total(termo: str) -> int:
        return sum(score for score, _ in mapa[termo]["artigos"])

    # Nunca-publicado primeiro; entre publicados, o menos recente; depois maior lastro; termo asc.
    angulo = min(
        elegiveis,
        key=lambda t: (t in publicados_set, ultima_posicao.get(t, -1), -score_total(t), t),
    )

    info = mapa[angulo]
    artigos_suporte = _artigos_suporte(info["artigos"], top_k, max_chars)
    eixo = info["pc"].eixo

    logger.info(
        "Ângulo escolhido: '%s' (eixo '%s', origem: %s, %d artigo(s) de suporte, cooldown: %s)",
        angulo,
        eixo,
        origem,
        len(artigos_suporte),
        ", ".join(dict.fromkeys(eixos_recentes(estado, cooldown_posts))) or "vazio",
    )
    return eixo, angulo, artigos_suporte
