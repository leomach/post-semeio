"""Leitura e validação de data/fontes.yaml."""
from dataclasses import dataclass

import yaml

from src.config import FONTES_PATH


@dataclass(frozen=True)
class Fonte:
    nome: str
    url_base: str
    ativo: bool


@dataclass(frozen=True)
class PalavraChave:
    termo: str
    peso: int
    eixo: str = "geral"


@dataclass(frozen=True)
class ConfigFontes:
    fontes: list[Fonte]
    palavras_chave: list[PalavraChave]


def carregar_fontes() -> ConfigFontes:
    with open(FONTES_PATH, "r", encoding="utf-8") as f:
        bruto = yaml.safe_load(f) or {}

    fontes = [
        Fonte(nome=item["nome"], url_base=item["url_base"], ativo=bool(item.get("ativo", False)))
        for item in bruto.get("fontes", [])
    ]
    palavras_chave = [
        PalavraChave(
            termo=item["termo"],
            peso=int(item.get("peso", 1)),
            eixo=str(item.get("eixo", "geral")),
        )
        for item in bruto.get("palavras_chave", [])
    ]

    return ConfigFontes(fontes=fontes, palavras_chave=palavras_chave)


def fontes_ativas(config: ConfigFontes) -> list[Fonte]:
    return [fonte for fonte in config.fontes if fonte.ativo]
