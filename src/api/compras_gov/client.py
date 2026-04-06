from __future__ import annotations

import logging
from typing import Any

import requests

from src.api.compras_gov.errors import ComprasGovError
from src.api.compras_gov.mapper import build_params


logger = logging.getLogger(__name__)

CONSULTAR_MATERIAL_URL = (
    "https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
)


def fetch_material_json(
    codigo_item: str,
    pagina: int = 1,
    tamanho_pagina: int = 500,
) -> dict[str, Any]:
    """
    Executa GET na API de consulta de material e retorna o corpo JSON.

    Responsável apenas por transporte HTTP e parse JSON bruto.
    """
    params = build_params(codigo_item, pagina, tamanho_pagina)

    try:
        response = requests.get(
            CONSULTAR_MATERIAL_URL,
            params=params,
            timeout=(5, 30),
        )
        response.raise_for_status()

    except requests.Timeout:
        logger.error(
            "Timeout na API Compras.gov.br | codigo_item=%s | pagina=%s",
            codigo_item,
            pagina,
        )
        raise ComprasGovError("Tempo de resposta excedido na consulta ao Compras.gov.br.")

    except requests.RequestException:
        logger.exception(
            "Erro HTTP na API Compras.gov.br | codigo_item=%s",
            codigo_item,
        )
        raise ComprasGovError("Falha na comunicação com o Compras.gov.br.")

    try:
        return response.json()
    except ValueError:
        logger.error("Resposta inválida (não JSON) da API Compras.gov.br")
        raise ComprasGovError("Resposta inválida recebida da API externa.")
