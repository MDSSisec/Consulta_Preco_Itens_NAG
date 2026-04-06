from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from src.api.serp_api.errors import SerpAPIError


logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"


def _build_params(termo: str, api_key: str, num: int) -> Dict[str, Any]:
    return {
        "engine": "google_shopping",
        "q": termo,
        "api_key": api_key,
        "hl": "pt-BR",
        "gl": "br",
        "num": num,
    }


def fetch_shopping_json(termo: str, api_key: str, num: int) -> dict[str, Any]:
    """
    Executa GET na SerpAPI e retorna o corpo JSON.

    Responsável apenas por transporte HTTP e parse JSON bruto.
    """
    params = _build_params(termo, api_key, num)

    try:
        response = requests.get(
            SERPAPI_ENDPOINT,
            params=params,
            timeout=(5, 30),
        )
        response.raise_for_status()

    except requests.Timeout:
        logger.error("Timeout ao consultar SerpAPI | termo=%s", termo)
        raise SerpAPIError("Tempo de resposta excedido ao consultar a API externa.")

    except requests.RequestException:
        logger.exception("Erro HTTP na SerpAPI | termo=%s", termo)
        raise SerpAPIError("Falha na comunicação com a API externa.")

    try:
        return response.json()
    except ValueError:
        logger.error("Resposta inválida (não JSON) da SerpAPI")
        raise SerpAPIError("Resposta inválida recebida da API externa.")
