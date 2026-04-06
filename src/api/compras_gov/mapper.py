from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd


logger = logging.getLogger(__name__)


def build_params(codigo_item: str, pagina: int, tamanho_pagina: int) -> Dict[str, Any]:
    return {
        "pagina": pagina,
        "tamanhoPagina": tamanho_pagina,
        "codigoItemCatalogo": str(codigo_item).strip(),
    }


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "descricaoItem": "Descrição do Item",
            "codigoItemCatalogo": "Cód. Catálogo",
            "quantidade": "Quantidade",
            "precoUnitario": "Preço Unitário (R$)",
            "nomeFornecedor": "Fornecedor",
            "estado": "UF",
            "dataCompra": "Data da Compra",
        }
    )


def items_to_dataframe(itens: List[dict]) -> pd.DataFrame:
    return pd.json_normalize(itens)


def material_payload_to_dataframe(data: dict[str, Any]) -> pd.DataFrame:
    """
    Converte o payload JSON da API em DataFrame com colunas de apresentação.

    Não realiza I/O; apenas transformação de estrutura.
    """
    itens = data.get("resultado", [])
    if not isinstance(itens, list):
        logger.warning("Formato inesperado do campo 'resultado'")
        return pd.DataFrame()

    if not itens:
        return pd.DataFrame()

    try:
        df = items_to_dataframe(itens)
    except Exception:
        logger.exception("Erro ao normalizar JSON para DataFrame")
        raise

    return normalize_dataframe(df)
