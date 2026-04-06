from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.api.serp_api.client import fetch_shopping_json
from src.api.serp_api.errors import SerpAPIError
from src.api.serp_api.mapper import shopping_json_to_results
from src.config.env import get_serpapi_api_key


logger = logging.getLogger(__name__)


def fetch_google_shopping(termo: str, num: int = 20) -> List[Dict[str, Any]]:
    """
    Orquestra cliente HTTP + mapeamento para lista de ofertas (Google Shopping).
    """
    api_key = get_serpapi_api_key()
    if not api_key:
        raise SerpAPIError(
            "Chave da SerpAPI não configurada. Defina SERPAPI_API_KEY no ambiente."
        )

    data = fetch_shopping_json(termo, api_key, num)
    results = shopping_json_to_results(data)

    logger.info(
        "SerpAPI retorno | termo=%s | resultados=%d",
        termo,
        len(results),
    )

    return results
