from __future__ import annotations

import os
import re
import logging
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"
GOOGLE_BASE_URL = "https://www.google.com"


class SerpAPIError(RuntimeError):
    """
    Exceção de domínio para erros relacionados à integração com a SerpAPI.

    Permite desacoplar falhas de infraestrutura (HTTP, timeout, parsing)
    da camada de aplicação (ex: controllers Flask), facilitando tratamento
    e padronização de mensagens ao usuário.
    """


def _normalize_link(link: Optional[str]) -> Optional[str]:
    """
    Normaliza URLs retornadas pela SerpAPI/Google Shopping.

    A API pode retornar links em diferentes formatos:
    - Caminhos relativos ("/shopping/product/...")
    - URLs completas ("https://...")
    - URLs sem esquema ("www.site.com/...")

    Args:
        link: URL original retornada pela API.

    Returns:
        URL absoluta válida ou None caso inválida.
    """
    if not link:
        return None

    s = str(link).strip()
    if not s:
        return None

    # Caminho relativo → prefixar domínio base do Google
    if s.startswith("/"):
        return f"{GOOGLE_BASE_URL}{s}"

    # URL já completa
    if s.startswith(("http://", "https://")):
        return s

    # Fallback: assume HTTPS
    return f"https://{s.lstrip('/')}"


def _parse_price_to_float(price_str: Optional[str]) -> Optional[float]:
    """
    Extrai e converte um valor monetário textual para float.

    A SerpAPI retorna preços em formatos variados, por exemplo:
    - "R$ 149,90 agora"
    - "a partir de R$ 12,34"
    - "R$ 1.234,56"
    - "R$ 10,00 - R$ 20,00"

    Estratégia:
    1. Remove símbolos monetários e normaliza string.
    2. Extrai o primeiro padrão numérico plausível.
    3. Converte considerando formatos BR ("," decimal) e US ("." decimal).

    Args:
        price_str: String de preço original.

    Returns:
        Valor float positivo ou None se não for possível interpretar.
    """
    if not price_str:
        return None

    s = str(price_str).strip()
    if not s:
        return None

    # Normalização básica de moeda e espaços
    normalized = (
        s.replace("\xa0", " ")
        .replace("R$", "")
        .replace("US$", "")
        .replace("€", "")
        .strip()
    )

    # Regex robusta para capturar números com ou sem separadores
    match = re.search(
        r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})|\d+(?:,\d{2})|\d+(?:\.\d{2})|\d+)",
        normalized,
    )

    if not match:
        return None

    num = match.group(1)

    try:
        # Formato BR → "1.234,56"
        if "," in num:
            num = num.replace(".", "").replace(",", ".")
        else:
            # Possível formato US → "1,234.56"
            if num.count(".") > 1:
                num = num.replace(".", "")
            num = num.replace(",", "")

        value = float(num)

        # Apenas valores positivos fazem sentido no contexto
        return value if value > 0 else None

    except ValueError:
        logger.debug("Falha ao converter preço: %s", price_str)
        return None


def _build_params(termo: str, api_key: str, num: int) -> Dict[str, Any]:
    """
    Constrói os parâmetros de requisição para a SerpAPI.

    Args:
        termo: Termo de busca.
        api_key: Chave da API.
        num: Quantidade de resultados desejados.

    Returns:
        Dicionário de parâmetros HTTP.
    """
    return {
        "engine": "google_shopping",
        "q": termo,
        "api_key": api_key,
        "hl": "pt-BR",  # idioma
        "gl": "br",     # localização geográfica
        "num": num,
    }


def _validate_api_key(api_key: str) -> None:
    """
    Valida a presença da chave da SerpAPI.

    Args:
        api_key: Chave obtida do ambiente.

    Raises:
        SerpAPIError: Caso a chave não esteja definida.
    """
    if not api_key:
        raise SerpAPIError(
            "Chave da SerpAPI não configurada. Defina SERPAPI_API_KEY no ambiente."
        )


def buscar_google_shopping(termo: str, num: int = 20) -> List[Dict[str, Any]]:
    """
    Realiza consulta de produtos no Google Shopping via SerpAPI.

    Esta função atua como camada de integração externa, sendo responsável por:
    - Orquestrar chamada HTTP
    - Validar respostas
    - Normalizar dados
    - Garantir resiliência a falhas parciais

    Args:
        termo: Texto de busca (ex: "mouse sem fio logitech").
        num: Quantidade de resultados desejados (default: 20).

    Returns:
        Lista de dicionários contendo:
            - title (str): Título do produto
            - price (str): Preço original (texto)
            - numeric_price (float | None): Preço convertido
            - currency (str | None): Moeda
            - source (str | None): Loja/origem
            - link (str | None): URL normalizada
            - position (int | None): Posição no ranking

    Raises:
        SerpAPIError: Em casos de erro de comunicação, timeout ou resposta inválida.
    """
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    _validate_api_key(api_key)

    params = _build_params(termo, api_key, num)

    try:
        response = requests.get(
            SERPAPI_ENDPOINT,
            params=params,
            timeout=(5, 30),  # (timeout de conexão, timeout de leitura)
        )
        response.raise_for_status()

    except requests.Timeout:
        logger.error("Timeout ao consultar SerpAPI | termo=%s", termo)
        raise SerpAPIError("Tempo de resposta excedido ao consultar a API externa.")

    except requests.RequestException as exc:
        logger.exception("Erro HTTP na SerpAPI | termo=%s", termo)
        raise SerpAPIError("Falha na comunicação com a API externa.") from exc

    try:
        data = response.json()
    except ValueError:
        logger.error("Resposta inválida (não JSON) da SerpAPI")
        raise SerpAPIError("Resposta inválida recebida da API externa.")

    items = data.get("shopping_results", [])
    if not isinstance(items, list):
        logger.warning("Formato inesperado de 'shopping_results'")
        return []

    results: List[Dict[str, Any]] = []

    for item in items:
        try:
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

        except Exception:
            # Fail-safe: garante que um item inválido não comprometa o restante
            logger.exception("Erro ao processar item da SerpAPI")
            continue

    logger.info(
        "SerpAPI retorno | termo=%s | resultados=%d",
        termo,
        len(results),
    )

    return results