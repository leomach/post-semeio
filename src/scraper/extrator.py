"""Scraping e extração de conteúdo: robots.txt, rate limit, circuit breaker, trafilatura."""
import logging
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import HTTP_TIMEOUT_SECONDS, MAX_RETRIES, RATE_LIMIT_SECONDS, USER_AGENT
from src.scraper.fontes import Fonte, PalavraChave

logger = logging.getLogger(__name__)

_ultima_requisicao_por_dominio: dict[str, float] = {}
_robots_cache: dict[str, RobotFileParser] = {}


def _dominio(url: str) -> str:
    return urlsplit(url).netloc


def _respeitar_rate_limit(url: str) -> None:
    dominio = _dominio(url)
    agora = time.monotonic()
    ultima = _ultima_requisicao_por_dominio.get(dominio)
    if ultima is not None:
        decorrido = agora - ultima
        if decorrido < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - decorrido)
    _ultima_requisicao_por_dominio[dominio] = agora


def pode_acessar(url: str) -> bool:
    partes = urlsplit(url)
    dominio = f"{partes.scheme}://{partes.netloc}"
    parser = _robots_cache.get(dominio)
    if parser is None:
        parser = RobotFileParser()
        robots_url = urljoin(dominio, "/robots.txt")
        try:
            # RobotFileParser.read() usa o User-Agent padrão do urllib, que alguns sites
            # bloqueiam com 403 — buscamos nós mesmos com nosso UA identificável (NFR 6.1)
            # e tratamos 403 nesse fetch como "não deu para ler", não como "tudo proibido".
            resposta = httpx.get(
                robots_url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True
            )
            if resposta.status_code == 404:
                parser.allow_all = True
            else:
                resposta.raise_for_status()
                parser.parse(resposta.text.splitlines())
        except Exception:
            logger.warning("Não foi possível ler robots.txt de %s — assumindo permitido", dominio)
            parser.allow_all = True
        _robots_cache[dominio] = parser
    return parser.can_fetch(USER_AGENT, url)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _buscar_html(url: str) -> str:
    _respeitar_rate_limit(url)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        resposta = client.get(url)
        resposta.raise_for_status()
        return resposta.text


def extrair_links_candidatos(fonte: Fonte, palavras_chave: list[PalavraChave]) -> list[tuple[str, int]]:
    """Retorna (url, peso) para links da página de listagem cujo texto casa com alguma palavra-chave."""
    html = _buscar_html(fonte.url_base)
    soup = BeautifulSoup(html, "lxml")
    dominio_base = _dominio(fonte.url_base)

    candidatos: dict[str, int] = {}
    for tag in soup.find_all("a", href=True):
        href = urljoin(fonte.url_base, tag["href"])
        if _dominio(href) != dominio_base:
            continue

        texto = tag.get_text(" ", strip=True).lower()
        if not texto:
            continue

        peso_total = sum(pc.peso for pc in palavras_chave if pc.termo.lower() in texto)
        if peso_total > 0:
            candidatos[href] = max(peso_total, candidatos.get(href, 0))

    return sorted(candidatos.items(), key=lambda item: item[1], reverse=True)


def extrair_conteudo(url: str) -> dict | None:
    html = _buscar_html(url)
    extraido = trafilatura.extract(
        html, url=url, output_format="json", with_metadata=True, favor_precision=True
    )
    if not extraido:
        return None

    import json as _json

    dados = _json.loads(extraido)
    corpo = (dados.get("text") or "").strip()
    if not corpo:
        return None

    return {
        "url": url,
        "titulo": dados.get("title") or "",
        "corpo": corpo,
        "data": dados.get("date"),
    }


def processar_fonte(
    fonte: Fonte,
    palavras_chave: list[PalavraChave],
    ja_processado_fn,
    max_falhas_consecutivas: int,
) -> list[dict]:
    """Varre uma fonte ativa e retorna artigos novos extraídos com sucesso."""
    if not pode_acessar(fonte.url_base):
        logger.warning("robots.txt bloqueia acesso a %s — pulando fonte", fonte.nome)
        return []

    try:
        candidatos = extrair_links_candidatos(fonte, palavras_chave)
    except Exception:
        logger.warning("Falha ao acessar listagem de %s — pulando fonte", fonte.nome, exc_info=True)
        return []

    artigos: list[dict] = []
    falhas_consecutivas = 0

    for url, peso in candidatos:
        if ja_processado_fn(url):
            continue

        if not pode_acessar(url):
            logger.warning("robots.txt bloqueia %s — pulando link", url)
            continue

        try:
            conteudo = extrair_conteudo(url)
        except Exception:
            falhas_consecutivas += 1
            logger.warning("Falha ao extrair %s (falha %d/%d)", url, falhas_consecutivas, max_falhas_consecutivas, exc_info=True)
            if falhas_consecutivas >= max_falhas_consecutivas:
                logger.warning("Circuit breaker acionado para fonte %s — abortando fonte", fonte.nome)
                break
            continue

        falhas_consecutivas = 0
        if conteudo:
            conteudo["fonte"] = fonte.nome
            conteudo["peso"] = peso
            artigos.append(conteudo)

    return artigos
