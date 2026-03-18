from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


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


def _to_numeric_br(series: pd.Series) -> pd.Series:
    """Converte strings pt-BR tipo 1.234,56 para float."""
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def processar_df(
    df: pd.DataFrame,
    coluna_preco: str = "Preço Unitário (R$)",
    config: Optional[CleaningConfig] = None,
) -> tuple[Optional[CleaningStats], Optional[pd.DataFrame]]:
    """
    Limpa e processa o DataFrame de preços.

    Regras principais:
    - Remove descrições com termos de kit/lote.
    - Mantém apenas unidade UN/UNIDADE (se colunas existirem).
    - Mantém apenas últimos N meses (se coluna de data existir).
    - Remove preços <= 0.
    - Remove valores acima de multiplicador × mediana.
    - Remove outliers via IQR.
    """
    if config is None:
        config = CleaningConfig()

    df = df.copy()
    if coluna_preco not in df.columns:
        raise KeyError(f"Coluna '{coluna_preco}' não encontrada no DataFrame.")

    # 1) filtro por descrição
    col_desc = next(
        (c for c in ["Descrição do Item", "descricaoItem"] if c in df.columns), None
    )
    if col_desc:
        desc = df[col_desc].astype(str).str.lower()
        padrao = "|".join(config.proibidas_descricao)
        df = df[~desc.str.contains(padrao, regex=True)]

    # 2) filtro por unidade
    col_unid = next(
        (c for c in ["siglaUnidadeFornecimento", "nomeUnidadeFornecimento"] if c in df.columns),
        None,
    )
    if col_unid:
        un = df[col_unid].astype(str).str.upper().str.strip()
        df = df[un.isin(list(config.unidades_permitidas))]

    # 3) filtro por data (últimos N meses), se existir
    col_data = next((c for c in ["Data da Compra", "dataCompra"] if c in df.columns), None)
    if col_data:
        df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
        limite = pd.Timestamp.today() - pd.DateOffset(months=config.meses_janela)
        df = df[df[col_data] >= limite]

    # 4) preço numérico
    df[coluna_preco] = _to_numeric_br(df[coluna_preco])
    df = df[df[coluna_preco] > 0]
    if df.empty:
        return None, None

    # 5) corte por multiplicador da mediana
    mediana = float(df[coluna_preco].median())
    if mediana > 0:
        limite_superior = config.multiplicador_mediana * mediana
        df = df[df[coluna_preco] <= limite_superior]
    if df.empty:
        return None, None

    # 6) IQR
    q1 = float(df[coluna_preco].quantile(0.25))
    q3 = float(df[coluna_preco].quantile(0.75))
    iqr = q3 - q1
    df_iqr = df[
        (df[coluna_preco] >= q1 - 1.5 * iqr) & (df[coluna_preco] <= q3 + 1.5 * iqr)
    ]
    if df_iqr.empty:
        df_iqr = df

    minimo = float(df_iqr[coluna_preco].min())
    maximo = float(df_iqr[coluna_preco].max())
    media = float(df_iqr[coluna_preco].mean())
    mediana_final = float(df_iqr[coluna_preco].median())
    iqr_min = float(df_iqr[coluna_preco].quantile(0.25))
    iqr_max = float(df_iqr[coluna_preco].quantile(0.75))

    stats = CleaningStats(
        minimo=minimo,
        maximo=maximo,
        media=media,
        mediana=mediana_final,
        iqr_min=iqr_min,
        iqr_max=iqr_max,
        n_registros=int(len(df_iqr)),
    )
    return stats, df_iqr

