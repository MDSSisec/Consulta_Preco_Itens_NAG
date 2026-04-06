"""Cliente HTTP (`client`), mapeamento (`mapper`) e erros (`errors`). Orquestração: `src.services.serp_api_service`."""

from .errors import SerpAPIError

__all__ = ["SerpAPIError"]
