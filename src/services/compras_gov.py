from __future__ import annotations

import pandas as pd
import requests


CONSULTAR_MATERIAL_URL = (
    "https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
)


def baixar_itens_catmat(codigo_item: str, pagina: int = 1, tamanho_pagina: int = 500) -> pd.DataFrame:
    """
    Consulta Compras.gov.br (CATMAT/material) e retorna DataFrame normalizado.
    """
    params = {
        "pagina": pagina,
        "tamanhoPagina": tamanho_pagina,
        "codigoItemCatalogo": str(codigo_item).strip(),
    }
    resp = requests.get(CONSULTAR_MATERIAL_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    itens = data.get("resultado", [])
    if not itens:
        return pd.DataFrame()

    df = pd.json_normalize(itens)
    df = df.rename(
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
    return df

