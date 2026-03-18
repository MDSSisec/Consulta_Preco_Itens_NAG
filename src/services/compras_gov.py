from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd
import requests


logger = logging.getLogger(__name__)

CONSULTAR_MATERIAL_URL = (
    "https://dadosabertos.compras.gov.br/modulo-pesquisa-preco/1_consultarMaterial"
)


class ComprasGovError(RuntimeError):
    """
    Exceção de domínio para erros na integração com a API do Compras.gov.br.

    Permite desacoplar falhas externas (HTTP, timeout, resposta inválida)
    da lógica de aplicação, facilitando tratamento padronizado na camada superior.
    """


def _build_params(codigo_item: str, pagina: int, tamanho_pagina: int) -> Dict[str, Any]:
    """
    Constrói os parâmetros da requisição para a API de consulta de materiais.

    Args:
        codigo_item: Código CATMAT do item.
        pagina: Número da página a ser consultada.
        tamanho_pagina: Quantidade de registros por página.

    Returns:
        Dicionário de parâmetros HTTP.
    """
    return {
        "pagina": pagina,
        "tamanhoPagina": tamanho_pagina,
        "codigoItemCatalogo": str(codigo_item).strip(),
    }


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza e padroniza os nomes das colunas do DataFrame.

    Essa etapa adapta os nomes técnicos da API para um formato mais
    amigável e consistente para exibição e análise.

    Args:
        df: DataFrame bruto retornado pela API.

    Returns:
        DataFrame com colunas renomeadas.
    """
    return df.rename(
        columns={
            "descricaoItem": "Descrição do Item",
            "codigoItemCatalogo": "Cód. Catálogo",
            "quantidade": "Quantidade",
            "precoUnitario": "Preço Unitário (R$)",
            "nomeFornecedor": "Fornecedor",
            "estado": "UF",
            "dataCompra": "Data da Compra",
        }
    )


def baixar_itens_catmat(
    codigo_item: str,
    pagina: int = 1,
    tamanho_pagina: int = 500,
) -> pd.DataFrame:
    """
    Consulta a API de dados abertos do Compras.gov.br para um código CATMAT
    e retorna os resultados em formato de DataFrame normalizado.

    Esta função atua como camada de integração externa, sendo responsável por:
    - Construir parâmetros de consulta
    - Executar requisição HTTP com controle de timeout
    - Validar resposta da API
    - Normalizar estrutura de dados (DataFrame)

    Args:
        codigo_item: Código do item no catálogo (CATMAT).
        pagina: Página de resultados (default: 1).
        tamanho_pagina: Quantidade de registros por página (default: 500).

    Returns:
        DataFrame contendo os registros retornados pela API.
        Retorna DataFrame vazio caso não haja resultados.

    Raises:
        ComprasGovError:
            - Em caso de timeout
            - Falha de comunicação HTTP
            - Resposta inválida (não JSON)
    """
    params = _build_params(codigo_item, pagina, tamanho_pagina)

    try:
        response = requests.get(
            CONSULTAR_MATERIAL_URL,
            params=params,
            timeout=(5, 30),  # (timeout de conexão, timeout de leitura)
        )
        response.raise_for_status()

    except requests.Timeout:
        logger.error(
            "Timeout na API Compras.gov.br | codigo_item=%s | pagina=%s",
            codigo_item,
            pagina,
        )
        raise ComprasGovError("Tempo de resposta excedido na consulta ao Compras.gov.br.")

    except requests.RequestException as exc:
        logger.exception(
            "Erro HTTP na API Compras.gov.br | codigo_item=%s",
            codigo_item,
        )
        raise ComprasGovError("Falha na comunicação com o Compras.gov.br.") from exc

    try:
        data = response.json()
    except ValueError:
        logger.error("Resposta inválida (não JSON) da API Compras.gov.br")
        raise ComprasGovError("Resposta inválida recebida da API externa.")

    itens = data.get("resultado", [])
    if not isinstance(itens, list):
        logger.warning("Formato inesperado do campo 'resultado'")
        return pd.DataFrame()

    if not itens:
        logger.info(
            "Nenhum resultado encontrado | codigo_item=%s | pagina=%s",
            codigo_item,
            pagina,
        )
        return pd.DataFrame()

    try:
        df = pd.json_normalize(itens)
    except Exception:
        logger.exception("Erro ao normalizar JSON para DataFrame")
        raise ComprasGovError("Falha ao processar os dados retornados pela API.")

    df = _normalize_dataframe(df)

    logger.info(
        "Consulta Compras.gov.br concluída | codigo_item=%s | registros=%d",
        codigo_item,
        len(df),
    )

    return df