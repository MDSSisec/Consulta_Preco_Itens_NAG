from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleaningConfig:
    meses_janela: int = 24
    multiplicador_mediana: float = 4.0
    proibidas_descricao: tuple[str, ...] = (
        "kit",
        "lote",
        "combo",
        "conjunto",
        "pack",
        "caixa",
        "estojo",
        "cx",
        "pacote",
    )
    unidades_permitidas: tuple[str, ...] = ("UN", "UNIDADE")


@dataclass(frozen=True)
class CleaningStats:
    minimo: float
    maximo: float
    media: float
    mediana: float
    iqr_min: float
    iqr_max: float
    n_registros: int
