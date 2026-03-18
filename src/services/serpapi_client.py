from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import requests


SERPAPI_ENDPOINT = "https://serpapi.com/search"
GOOGLE_BASE_URL = "https://www.google.com"


def _normalize_link(link: Optional[str]) -> Optional[str]:
    if not link:
        return None
    s = str(link).strip()
    if not s:
        return None
    if s.startswith("/"):
        return f"{GOOGLE_BASE_URL}{s}"
    if s.startswith("http://") or s.startswith("https://"):
        return s
    # Alguns resultados podem vir como "www..." ou sem esquema
    return f"https://{s.lstrip('/')}"


def _parse_price_to_float(price_str: Optional[str]) -> Optional[float]:
    if not price_str:
        return None
    s = str(price_str).strip()
    if not s:
        return None

    # SerpAPI/Google Shopping frequentemente retorna strings como:
    # "R$ 149,90 agora", "a partir de R$ 12,34", "R$ 1.234,56", "R$ 10,00 - R$ 20,00"
    # Aqui extraímos o primeiro número com cara de preço e ignoramos sufixos.
    normalized = s.replace("\xa0", " ").strip()
    normalized = normalized.replace("R$", "").replace("US$", "").replace("€", "")

    m = re.search(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:,\d{2})|\d+(?:\.\d{2})|\d+)",
        normalized,
    )
    if not m:
        return None

    num = m.group(1)
    # Formato BR: milhares com "." e decimal com ","
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    else:
        # Se vier no formato US "1,234.56" (raro aqui), remover separadores de milhar ","
        # e manter o "." decimal.
        if num.count(".") > 1:
            num = num.replace(".", "")
        num = num.replace(",", "")

    try:
        val = float(num)
    except ValueError:
        return None
    return val if val > 0 else None


def buscar_google_shopping(termo: str, num: int = 20) -> List[Dict[str, Any]]:
    """
    Busca no Google Shopping via SerpAPI.

    Requer variável de ambiente:
    - SERPAPI_API_KEY
    """
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Defina SERPAPI_API_KEY no arquivo .env para usar a SerpAPI.")

    params = {
        "engine": "google_shopping",
        "q": termo,
        "api_key": api_key,
        "hl": "pt-BR",
        "gl": "br",
        "num": num,
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results: List[Dict[str, Any]] = []
    for item in data.get("shopping_results", []):
        numeric_price = _parse_price_to_float(item.get("price"))
        link = _normalize_link(item.get("link"))
        results.append(
            {
                "title": item.get("title"),
                "price": item.get("price"),
                "numeric_price": numeric_price,
                "currency": item.get("currency"),
                "source": item.get("source"),
                "link": link,
                "position": item.get("position"),
            }
        )
    return results

