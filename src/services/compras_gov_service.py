from __future__ import annotations

import logging

import pandas as pd

from src.api.compras_gov.client import fetch_material_json
from src.api.compras_gov.errors import ComprasGovError
from src.api.compras_gov.mapper import material_payload_to_dataframe


logger = logging.getLogger(__name__)


def fetch_compras_gov(
    codigo_item: str,
    pagina: int = 1,
    tamanho_pagina: int = 500,
) -> pd.DataFrame:
    """
    Orquestra cliente HTTP + mapeamento para DataFrame normalizado (CATMAT).
    """
    data = fetch_material_json(codigo_item, pagina, tamanho_pagina)

    try:
        df = material_payload_to_dataframe(data)
    except Exception as exc:
        raise ComprasGovError("Falha ao processar os dados retornados pela API.") from exc

    if df.empty:
        resultado = data.get("resultado", [])
        if isinstance(resultado, list) and len(resultado) == 0:
            logger.info(
                "Nenhum resultado encontrado | codigo_item=%s | pagina=%s",
                codigo_item,
                pagina,
            )
    else:
        logger.info(
            "Consulta Compras.gov.br concluída | codigo_item=%s | registros=%d",
            codigo_item,
            len(df),
        )

    return df
