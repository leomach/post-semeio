"""Wrapper fino sobre o SDK google-genai (retry, timeout, sem log de credenciais).

Observações sobre retry (verificado no SDK google-genai instalado):
- O SDK NÃO faz retry por conta própria com a config padrão: `HttpOptions.retry_options`
  é None, e nesse caso ele usa `stop_after_attempt(1)` (uma única tentativa). Portanto o
  retry desta camada NÃO é aninhado/multiplicado com nenhum retry interno do SDK.
- Só retentamos erros genuinamente transitórios (429/500/502/503/504 e timeouts/erros de
  conexão). Erros definitivos como 404 (modelo inexistente) ou 400 (requisição inválida)
  falham de imediato, sem desperdiçar chamadas.
- Quando o servidor devolve um `RetryInfo.retryDelay` (ex.: "retry in 24s"), respeitamos
  esse tempo em vez do backoff exponencial — evita bater de novo antes da janela pedida.
"""
import logging
import os
import re

import httpx
from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import GEMINI_MODEL, LLM_TIMEOUT_SECONDS, MAX_RETRIES, RETRY_WAIT_MAX_SECONDS

logger = logging.getLogger(__name__)

# Status HTTP transitórios (mesma lista que o próprio SDK considera retryável).
STATUS_TRANSITORIOS = {408, 429, 500, 502, 503, 504}

_client: genai.Client | None = None


def _obter_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada no ambiente")
        _client = genai.Client(api_key=api_key)
    return _client


def _erro_transitorio(exc: BaseException) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code in STATUS_TRANSITORIOS
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, RuntimeError)):
        # RuntimeError aqui = "Resposta vazia do Gemini" (transitório, vale nova tentativa).
        return True
    return False


def _retry_delay_do_servidor(exc: BaseException) -> float | None:
    """Extrai o RetryInfo.retryDelay (em segundos) do corpo do erro, se houver."""
    if not isinstance(exc, errors.APIError):
        return None
    detalhes = getattr(exc, "details", None)
    if not isinstance(detalhes, dict):
        return None
    violacoes = detalhes.get("error", {}).get("details", [])
    for item in violacoes:
        if isinstance(item, dict) and item.get("@type", "").endswith("RetryInfo"):
            bruto = item.get("retryDelay", "")
            m = re.match(r"([0-9.]+)s?", str(bruto))
            if m:
                return float(m.group(1))
    return None


def _esperar(retry_state) -> float:
    """Wait híbrido: respeita o retryDelay do servidor; senão, backoff exponencial."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    sugerido = _retry_delay_do_servidor(exc) if exc else None
    exponencial = wait_exponential(multiplier=1, min=2, max=RETRY_WAIT_MAX_SECONDS)(retry_state)
    if sugerido is not None:
        # Nunca esperar menos do que o servidor pediu; teto em RETRY_WAIT_MAX_SECONDS.
        return min(max(sugerido, exponencial), RETRY_WAIT_MAX_SECONDS)
    return exponencial


def gerar(prompt: str) -> str:
    """Envia um prompt ao Gemini e retorna o texto de resposta."""
    client = _obter_client()
    return _gerar_com_retry(client, prompt)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_esperar,
    retry=retry_if_exception(_erro_transitorio),
    reraise=True,
)
def _gerar_com_retry(client: genai.Client, prompt: str) -> str:
    resposta = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=int(LLM_TIMEOUT_SECONDS * 1000)),
        ),
    )
    texto = (resposta.text or "").strip()
    if not texto:
        raise RuntimeError("Resposta vazia do Gemini")
    return texto
