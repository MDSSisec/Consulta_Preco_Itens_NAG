from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

GOOGLE_BASE_URL = "https://www.google.com"


def normalize_link(link: Optional[str]) -> Optional[str]:
    if not link:
        return None

    s = str(link).strip()
    if not s:
        return None

    if s.startswith("/"):
        return f"{GOOGLE_BASE_URL}{s}"

    if s.startswith(("http://", "https://")):
        return s

    return f"https://{s.lstrip('/')}"


def parse_price_to_float(price_str: Optional[str]) -> Optional[float]:
    if not price_str:
        return None

    s = str(price_str).strip()
    if not s:
        return None

    normalized = (
        s.replace("\xa0", " ")
        .replace("R$", "")
        .replace("US$", "")
        .replace("€", "")
        .strip()
    )

    match = re.search(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:,\d{2})|\d+(?:\.\d{2})|\d+)",
        normalized,
    )

    if not match:
        return None

    num = match.group(1)

    try:
        if "," in num:
            num = num.replace(".", "").replace(",", ".")
        else:
            if num.count(".") > 1:
                num = num.replace(".", "")
            num = num.replace(",", "")

        value = float(num)
        return value if value > 0 else None

    except ValueError:
        logger.debug("Falha ao converter preço: %s", price_str)
        return None


def map_shopping_item(item: dict) -> Dict[str, Any]:
    numeric_price = parse_price_to_float(item.get("price"))
    link = normalize_link(item.get("link"))
    return {
        "title": item.get("title"),
        "price": item.get("price"),
        "numeric_price": numeric_price,
        "currency": item.get("currency"),
        "source": item.get("source"),
        "link": link,
        "position": item.get("position"),
    }


def shopping_json_to_results(data: dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrai e normaliza resultados de shopping a partir do JSON da SerpAPI.
    """
    items = data.get("shopping_results", [])
    if not isinstance(items, list):
        logger.warning("Formato inesperado de 'shopping_results'")
        return []

    results: List[Dict[str, Any]] = []

    for item in items:
        try:
            results.append(map_shopping_item(item))
        except Exception:
            logger.exception("Erro ao processar item da SerpAPI")
            continue

    return results
