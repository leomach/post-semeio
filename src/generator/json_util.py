"""Utilitário de parsing defensivo de JSON vindo do LLM."""
import re

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def limpar_json(texto: str) -> str:
    """Remove code fences residuais (```json ... ```) e espaços das bordas."""
    return _FENCE_RE.sub("", texto.strip()).strip()
