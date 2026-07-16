"""Normalização de URL, hashing e checagem de histórico contra estado.json."""
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from src.config import ESTADO_PATH

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid",
}


def normalizar_url(url: str) -> str:
    partes = urlsplit(url.strip())
    scheme = partes.scheme.lower() or "https"
    netloc = partes.netloc.lower()
    path = partes.path.rstrip("/") or "/"

    query_pairs = [
        (chave, valor)
        for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
        if chave.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_pairs))

    return urlunsplit((scheme, netloc, path, query, ""))


def calcular_hash(url_normalizada: str) -> str:
    return hashlib.sha256(url_normalizada.encode("utf-8")).hexdigest()


def carregar_estado() -> dict:
    if not ESTADO_PATH.exists():
        return {"links_processados": {}}
    with open(ESTADO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_estado(estado: dict) -> None:
    ESTADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ESTADO_PATH, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ja_processado(url: str, estado: dict) -> bool:
    hash_url = calcular_hash(normalizar_url(url))
    return hash_url in estado.get("links_processados", {})


def registrar_processado(url: str, fonte: str, titulo: str, estado: dict) -> str:
    hash_url = calcular_hash(normalizar_url(url))
    estado.setdefault("links_processados", {})[hash_url] = {
        "url": url,
        "fonte": fonte,
        "titulo": titulo,
        "processado_em": datetime.now(timezone.utc).isoformat(),
    }
    return hash_url
