"""Fachada: erros das integrações + orquestração em `services/`."""

from src.api.compras_gov import ComprasGovError
from src.api.serp_api import SerpAPIError
from src.services.compras_gov_service import fetch_compras_gov
from src.services.serp_api_service import fetch_google_shopping

__all__ = [
    "ComprasGovError",
    "SerpAPIError",
    "fetch_compras_gov",
    "fetch_google_shopping",
]
