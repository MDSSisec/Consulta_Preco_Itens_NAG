"""Pacote da aplicação (importe subpacotes conforme a camada)."""

from src.api import ComprasGovError, SerpAPIError, fetch_compras_gov, fetch_google_shopping
from src.domain import CleaningConfig, CleaningStats

__all__ = [
    "CleaningConfig",
    "CleaningStats",
    "ComprasGovError",
    "SerpAPIError",
    "fetch_compras_gov",
    "fetch_google_shopping",
]
