"""Deriva carrossel + legenda a partir do artigo (RF10-RF12)."""
import json

from src.config import (
    CARROSSEL_MAX_SLIDES,
    CARROSSEL_MIN_HASHTAGS,
    CARROSSEL_MIN_SLIDES,
    CARROSSEL_PATH,
)
from src.generator.json_util import limpar_json
from src.generator.llm_client import gerar
from src.generator.prompts.artigo import PERSONA_ALVO, TOM_DE_VOZ
from src.generator.prompts.carrossel import montar_prompt_carrossel


def _validar_carrossel(dados: dict) -> None:
    slides = dados.get("slides")
    if not isinstance(slides, list) or not (CARROSSEL_MIN_SLIDES <= len(slides) <= CARROSSEL_MAX_SLIDES):
        raise ValueError(
            f"Carrossel deve ter entre {CARROSSEL_MIN_SLIDES} e {CARROSSEL_MAX_SLIDES} slides, "
            f"obtido: {len(slides) if isinstance(slides, list) else 'inválido'}"
        )
    if not dados.get("legenda", "").strip():
        raise ValueError("Legenda do carrossel está vazia")
    hashtags = dados.get("hashtags")
    if not isinstance(hashtags, list) or len(hashtags) < CARROSSEL_MIN_HASHTAGS:
        raise ValueError(f"Carrossel deve ter ao menos {CARROSSEL_MIN_HASHTAGS} hashtags")


def gerar_carrossel(artigo_markdown: str) -> dict:
    prompt = montar_prompt_carrossel(artigo_markdown, TOM_DE_VOZ, PERSONA_ALVO)
    resposta = gerar(prompt)

    resposta_limpa = limpar_json(resposta)
    try:
        dados = json.loads(resposta_limpa)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Resposta do LLM não é JSON válido: {exc}") from exc

    _validar_carrossel(dados)

    CARROSSEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CARROSSEL_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return dados
