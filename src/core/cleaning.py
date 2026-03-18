from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class CleaningConfig:
    """
    Configuração de regras de limpeza e filtragem de dados.

    Attributes:
        meses_janela: Quantidade de meses retroativos considerados válidos.
        multiplicador_mediana: Limite superior baseado na mediana (anti-outliers extremos).
        proibidas_descricao: Termos que indicam agrupamento (kit/lote) e devem ser excluídos.
        unidades_permitidas: Unidades válidas (evita distorção por caixa/pacote/etc).
    """
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
    """
    Estrutura de saída com métricas estatísticas pós-limpeza.

    Attributes:
        minimo: Menor preço válido
        maximo: Maior preço válido
        media: Média aritmética
        mediana: Mediana (robusta contra outliers)
        iqr_min: Primeiro quartil (Q1)
        iqr_max: Terceiro quartil (Q3)
        n_registros: Quantidade de registros considerados
    """
    minimo: float
    maximo: float
    media: float
    mediana: float
    iqr_min: float
    iqr_max: float
    n_registros: int


def _to_numeric_br(series: pd.Series) -> pd.Series:
    """
    Converte valores monetários no formato brasileiro (pt-BR) para float.

    Exemplo:
        "1.234,56" → 1234.56

    Estratégia:
        - Remove separador de milhar (.)
        - Converte vírgula decimal para ponto
        - Força conversão numérica (coerce → NaN em erros)

    Args:
        series: Série contendo valores monetários como string.

    Returns:
        Série numérica (float), com NaN para valores inválidos.
    """
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def processar_df(
    df: pd.DataFrame,
    coluna_preco: str = "Preço Unitário (R$)",
    config: Optional[CleaningConfig] = None,
) -> Tuple[Optional[CleaningStats], Optional[pd.DataFrame]]:
    """
    Pipeline de limpeza e padronização de dados de preços.

    Etapas do pipeline:

    1. Filtro por descrição
        - Remove itens agregados (kits, combos, caixas)
        - Garante comparabilidade unitária

    2. Filtro por unidade
        - Mantém apenas unidades equivalentes (UN/UNIDADE)
        - Evita distorções por volume/embalagem

    3. Filtro temporal
        - Mantém apenas registros recentes (janela configurável)
        - Evita preços defasados

    4. Normalização de preço
        - Converte string → float
        - Remove valores inválidos ou <= 0

    5. Corte por mediana (robust filtering)
        - Remove valores extremos acima de (multiplicador × mediana)
        - Protege contra outliers absurdos (ex: erro de digitação)

    6. Remoção de outliers via IQR
        - Método estatístico clássico (Q1 - 1.5*IQR, Q3 + 1.5*IQR)
        - Caso elimine tudo, fallback para dataset anterior

    Args:
        df: DataFrame bruto vindo da API.
        coluna_preco: Nome da coluna de preço.
        config: Configuração de limpeza (opcional).

    Returns:
        Tuple contendo:
            - CleaningStats (ou None se dataset inválido)
            - DataFrame limpo (ou None)
    """
    if config is None:
        config = CleaningConfig()

    df = df.copy()

    if coluna_preco not in df.columns:
        raise KeyError(f"Coluna '{coluna_preco}' não encontrada no DataFrame.")

    # ---------------------------------------------------
    # 1) FILTRO POR DESCRIÇÃO (remoção de agregações)
    # ---------------------------------------------------
    col_desc = next(
        (c for c in ["Descrição do Item", "descricaoItem"] if c in df.columns),
        None,
    )

    if col_desc:
        desc = df[col_desc].astype(str).str.lower()
        padrao = "|".join(config.proibidas_descricao)
        df = df[~desc.str.contains(padrao, regex=True)]

    # ---------------------------------------------------
    # 2) FILTRO POR UNIDADE
    # ---------------------------------------------------
    col_unid = next(
        (c for c in ["siglaUnidadeFornecimento", "nomeUnidadeFornecimento"] if c in df.columns),
        None,
    )

    if col_unid:
        un = df[col_unid].astype(str).str.upper().str.strip()
        df = df[un.isin(list(config.unidades_permitidas))]

    # ---------------------------------------------------
    # 3) FILTRO TEMPORAL
    # ---------------------------------------------------
    col_data = next(
        (c for c in ["Data da Compra", "dataCompra"] if c in df.columns),
        None,
    )

    if col_data:
        df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
        limite = pd.Timestamp.today() - pd.DateOffset(months=config.meses_janela)
        df = df[df[col_data] >= limite]

    # ---------------------------------------------------
    # 4) NORMALIZAÇÃO DE PREÇO
    # ---------------------------------------------------
    df[coluna_preco] = _to_numeric_br(df[coluna_preco])
    df = df[df[coluna_preco] > 0]

    if df.empty:
        return None, None

    # ---------------------------------------------------
    # 5) CORTE POR MEDIANA (robusto contra extremos)
    # ---------------------------------------------------
    mediana = float(df[coluna_preco].median())

    if mediana > 0:
        limite_superior = config.multiplicador_mediana * mediana
        df = df[df[coluna_preco] <= limite_superior]

    if df.empty:
        return None, None

    # ---------------------------------------------------
    # 6) OUTLIERS VIA IQR
    # ---------------------------------------------------
    q1 = float(df[coluna_preco].quantile(0.25))
    q3 = float(df[coluna_preco].quantile(0.75))
    iqr = q3 - q1

    df_iqr = df[
        (df[coluna_preco] >= q1 - 1.5 * iqr)
        & (df[coluna_preco] <= q3 + 1.5 * iqr)
    ]

    # Fallback: evita eliminar todos os dados
    if df_iqr.empty:
        df_iqr = df

    # ---------------------------------------------------
    # 7) ESTATÍSTICAS FINAIS
    # ---------------------------------------------------
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