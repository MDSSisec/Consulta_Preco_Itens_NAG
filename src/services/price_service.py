from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.domain.cleaning import CleaningConfig, CleaningStats
from src.utils.format_price import formatar_preco


def _to_numeric_br(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def processar_df(
    df: pd.DataFrame,
    coluna_preco: str = "Preço Unitário (R$)",
    config: Optional[CleaningConfig] = None,
) -> Tuple[Optional[CleaningStats], Optional[pd.DataFrame]]:
    """
    Pipeline de limpeza e padronização de dados de preços (CATMAT).
    """
    if config is None:
        config = CleaningConfig()

    df = df.copy()

    if coluna_preco not in df.columns:
        raise KeyError(f"Coluna '{coluna_preco}' não encontrada no DataFrame.")

    col_desc = next(
        (c for c in ["Descrição do Item", "descricaoItem"] if c in df.columns),
        None,
    )

    if col_desc:
        desc = df[col_desc].astype(str).str.lower()
        padrao = "|".join(config.proibidas_descricao)
        df = df[~desc.str.contains(padrao, regex=True)]

    col_unid = next(
        (c for c in ["siglaUnidadeFornecimento", "nomeUnidadeFornecimento"] if c in df.columns),
        None,
    )

    if col_unid:
        un = df[col_unid].astype(str).str.upper().str.strip()
        df = df[un.isin(list(config.unidades_permitidas))]

    col_data = next(
        (c for c in ["Data da Compra", "dataCompra"] if c in df.columns),
        None,
    )

    if col_data:
        df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
        limite = pd.Timestamp.today() - pd.DateOffset(months=config.meses_janela)
        df = df[df[col_data] >= limite]

    df[coluna_preco] = _to_numeric_br(df[coluna_preco])
    df = df[df[coluna_preco] > 0]

    if df.empty:
        return None, None

    mediana = float(df[coluna_preco].median())

    if mediana > 0:
        limite_superior = config.multiplicador_mediana * mediana
        df = df[df[coluna_preco] <= limite_superior]

    if df.empty:
        return None, None

    q1 = float(df[coluna_preco].quantile(0.25))
    q3 = float(df[coluna_preco].quantile(0.75))
    iqr = q3 - q1

    df_iqr = df[
        (df[coluna_preco] >= q1 - 1.5 * iqr)
        & (df[coluna_preco] <= q3 + 1.5 * iqr)
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


def build_compras_stats_view(stats: CleaningStats, total_original: int) -> Dict[str, Any]:
    return {
        "n_registros_validos": stats.n_registros,
        "n_registros_totais": total_original,
        "min_fmt": formatar_preco(stats.minimo),
        "max_fmt": formatar_preco(stats.maximo),
        "media_fmt": formatar_preco(stats.media),
        "mediana_fmt": formatar_preco(stats.mediana),
        "iqr_min_fmt": formatar_preco(stats.iqr_min),
        "iqr_max_fmt": formatar_preco(stats.iqr_max),
    }


def preparar_tabela_compras(df: pd.DataFrame) -> tuple[List[Dict[str, str]], List[str]]:
    colunas_preferidas = [
        "Descrição do Item",
        "Cód. Catálogo",
        "Quantidade",
        "Preço Unitário (R$)",
        "Fornecedor",
        "UF",
        "Data da Compra",
    ]

    colunas = [c for c in colunas_preferidas if c in df.columns]

    df_ord = df.copy()

    if "Preço Unitário (R$)" in df_ord.columns:
        df_ord = df_ord.sort_values(by="Preço Unitário (R$)")
        df_ord["Preço Unitário (R$)"] = df_ord["Preço Unitário (R$)"].apply(formatar_preco)

    df_view = df_ord[colunas] if colunas else df_ord.head(100)

    linhas: List[Dict[str, str]] = []

    for _, row in df_view.iterrows():
        linha: Dict[str, str] = {}

        for col in colunas:
            val = row.get(col)

            if pd.isna(val):
                linha[col] = ""

            elif hasattr(val, "strftime"):
                linha[col] = val.strftime("%d / %m / %Y")

            else:
                linha[col] = str(val)

        linhas.append(linha)

    return linhas, colunas


def _percentile_sorted(values_sorted: list[float], p: float) -> float:
    """
    Percentil com interpolação linear (p em [0, 1]).
    Espera a lista já ordenada.
    """
    if not values_sorted:
        raise ValueError("Lista vazia")
    if p <= 0:
        return float(values_sorted[0])
    if p >= 1:
        return float(values_sorted[-1])

    n = len(values_sorted)
    pos = (n - 1) * p
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    if hi == lo:
        return float(values_sorted[lo])
    return float(values_sorted[lo]) * (1 - frac) + float(values_sorted[hi]) * frac


def calcular_estatisticas_serpapi(resultados: list[Dict[str, Any]]) -> Dict[str, Any] | None:
    n_totais = len(resultados)

    comparaveis: list[Dict[str, Any]] = []
    n_incomparaveis = 0
    for r in resultados:
        if r.get("is_comparable") is False:
            n_incomparaveis += 1
            continue
        comparaveis.append(r)

    precos = [
        float(r["numeric_price"])
        for r in comparaveis
        if isinstance(r.get("numeric_price"), (int, float)) and float(r["numeric_price"]) > 0
    ]

    if not precos:
        return None

    precos_sorted = sorted(precos)

    # Quartis via percentis (mais estável para n par/ímpar e para listas pequenas)
    q1 = _percentile_sorted(precos_sorted, 0.25)
    q3 = _percentile_sorted(precos_sorted, 0.75)
    iqr = q3 - q1

    # Remoção de outliers pelo IQR (1,5x)
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    precos_sem_outliers = [p for p in precos_sorted if limite_inferior <= p <= limite_superior]
    n_outliers = len(precos_sorted) - len(precos_sem_outliers)
    base = precos_sem_outliers if precos_sem_outliers else precos_sorted
    base_sorted = sorted(base)

    minimo = min(base_sorted)
    maximo = max(base_sorted)
    media = statistics.mean(base_sorted)
    mediana = statistics.median(base_sorted)

    q1_base = _percentile_sorted(base_sorted, 0.25)
    q3_base = _percentile_sorted(base_sorted, 0.75)

    return {
        "n_registros_validos": len(base_sorted),
        "n_registros_totais": n_totais,
        "n_filtrados_incomparaveis": n_incomparaveis,
        "n_outliers_removidos": n_outliers,
        "min_fmt": formatar_preco(minimo),
        "max_fmt": formatar_preco(maximo),
        "media_fmt": formatar_preco(media),
        "mediana_fmt": formatar_preco(mediana),
        "iqr_min_fmt": formatar_preco(q1_base),
        "iqr_max_fmt": formatar_preco(q3_base),
    }


def formatar_precos_serpapi(resultados: list[Dict[str, Any]]) -> None:
    for item in resultados:
        np = item.get("numeric_price")
        if isinstance(np, (int, float)) and np > 0:
            item["price"] = formatar_preco(float(np))
