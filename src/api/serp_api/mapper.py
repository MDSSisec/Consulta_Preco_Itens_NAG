from __future__ import annotations

import logging
import re
import unicodedata
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
        .replace("$", "")
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


def _normalize_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = str(s).strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _extract_capacity_liters(title_norm: str) -> Optional[int]:
    if not title_norm:
        return None

    # Ex.: "50L", "60 l", "80 litros"
    m = re.search(r"\b(\d{2,3})\s*(?:l|litros?)\b", title_norm)
    if not m:
        return None

    try:
        v = int(m.group(1))
        return v if v > 0 else None
    except ValueError:
        return None


def _extract_capacity_kg(title_norm: str) -> Optional[int]:
    if not title_norm:
        return None

    # Ex.: "75kg", "40 kg"
    m = re.search(r"\b(\d{2,4})\s*kg\b", title_norm)
    if not m:
        return None

    try:
        v = int(m.group(1))
        return v if v > 0 else None
    except ValueError:
        return None


def _classify_shopping_title(title: Optional[str]) -> Dict[str, Any]:
    """
    Classificação heurística para reduzir mistura de itens não comparáveis.

    Objetivo: sinalizar itens que fogem do "carrinho de mão com caçamba" (carriola),
    como carrinhos dobráveis/multiuso para carga/compras.
    """
    title_norm = _normalize_text(title)
    if not title_norm:
        return {
            "title_normalized": "",
            "category": "desconhecido",
            "is_comparable": True,
            "capacity_liters": None,
            "capacity_kg": None,
            "classification_reasons": [],
        }

    reasons: list[str] = []

    has_cart = "carrinho" in title_norm
    wheelbarrow_terms = (
        "carrinho de mao" in title_norm
        or "carriola" in title_norm
        or "cambaca" in title_norm  # common OCR/typo; keep permissive
        or "cacamba" in title_norm
        or "girica" in title_norm
    )

    folding_terms = any(
        t in title_norm
        for t in [
            "dobravel",
            "escamoteavel",
            "retratil",
        ]
    )

    multiuse_terms = any(
        t in title_norm
        for t in [
            "multiuso",
            "compras",
            "transporte",
            "carga",
            "estoque",
            "corda",
        ]
    )

    capacity_liters = _extract_capacity_liters(title_norm)
    capacity_kg = _extract_capacity_kg(title_norm)

    if folding_terms:
        reasons.append("dobravel/escamoteavel/retratil")
    if multiuse_terms:
        reasons.append("multiuso/compras/carga/transporte")

    # Para consulta genérica "carrinho de mão", capacidades muito altas (ex.: 112L/140L)
    # costumam ser outro subproduto (jiricão/girica grande) e distorcem o resumo.
    litros_fora_faixa = capacity_liters is not None and (capacity_liters < 30 or capacity_liters > 100)
    if litros_fora_faixa:
        reasons.append("capacidade_litros_fora_faixa")

    # Sinais de "carriola/carrinho de mão" de construção: caçamba e/ou litros
    has_wheelbarrow_shape = ("cacamba" in title_norm) or (capacity_liters is not None)

    # Heurística de comparabilidade:
    # - Se parece carrinho de mão (termos de caçamba/carriola) -> comparável.
    # - Se tem sinais de dobrável/multiuso e NÃO tem sinais de caçamba/litros -> não comparável
    #   (mesmo que o título contenha "carrinho de mão", que é ambíguo em marketplace).
    # - Caso contrário, mantém como comparável (fail-open) para não perder itens legítimos.
    if litros_fora_faixa:
        category = "outro"
        is_comparable = False
    elif (folding_terms or multiuse_terms) and not has_wheelbarrow_shape:
        category = "carrinho_dobravel_ou_carga"
        is_comparable = False
    elif wheelbarrow_terms:
        category = "carrinho_de_mao"
        is_comparable = True
    else:
        category = "outro"
        is_comparable = True

    return {
        "title_normalized": title_norm,
        "category": category,
        "is_comparable": is_comparable,
        "capacity_liters": capacity_liters,
        "capacity_kg": capacity_kg,
        "classification_reasons": reasons,
    }


def _numeric_price_from_item(item: dict) -> Optional[float]:
    """Prioriza `extracted_price` da SerpAPI (Google Shopping); senão faz parse do texto `price`."""
    raw = item.get("extracted_price")
    if raw is not None and raw != "":
        try:
            v = float(raw)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    return parse_price_to_float(item.get("price"))


def map_shopping_item(item: dict) -> Dict[str, Any]:
    # API atual: product_link; formato antigo: link
    raw_url = item.get("product_link") or item.get("link")
    link = normalize_link(raw_url)
    numeric_price = _numeric_price_from_item(item)
    classification = _classify_shopping_title(item.get("title"))
    return {
        "title": item.get("title"),
        "title_normalized": classification["title_normalized"],
        "price": item.get("price"),
        "numeric_price": numeric_price,
        "currency": item.get("currency"),
        "source": item.get("source"),
        "link": link,
        "product_id": item.get("product_id"),
        "position": item.get("position"),
        "rating": item.get("rating"),
        "reviews": item.get("reviews"),
        "snippet": item.get("snippet"),
        "delivery": item.get("delivery"),
        "thumbnail": item.get("thumbnail") or item.get("serpapi_thumbnail"),
        "multiple_sources": item.get("multiple_sources"),
        "source_icon": item.get("source_icon"),
        "category": classification["category"],
        "is_comparable": classification["is_comparable"],
        "capacity_liters": classification["capacity_liters"],
        "capacity_kg": classification["capacity_kg"],
        "classification_reasons": classification["classification_reasons"],
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
