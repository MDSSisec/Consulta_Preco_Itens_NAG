from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

import pandas as pd
from flask import Blueprint, redirect, render_template, request, url_for

from src.core.cleaning import processar_df
from src.core.formatting import formatar_preco
from src.services.compras_gov import baixar_itens_catmat


logger = logging.getLogger(__name__)

compras_bp = Blueprint("compras", __name__)

# Armazenamento temporário (in-memory) para padrão PRG (Post/Redirect/Get)
_ONE_TIME_COMPRAS: Dict[str, Dict[str, Any]] = {}

# Limite de controle de memória
_ONE_TIME_MAX = 20


def _build_stats_view(stats: Any, total_original: int) -> Dict[str, Any]:
    """
    Constrói estrutura de estatísticas formatadas para a camada de apresentação.

    Args:
        stats: Objeto retornado por `processar_df` contendo métricas numéricas.
        total_original: Quantidade total de registros antes da limpeza.

    Returns:
        Dicionário com métricas formatadas para exibição.
    """
    return {
        "n_registros_validos": stats.n_registros,
        "n_registros_totais": total_original,
        "min_fmt": formatar_preco(stats.minimo),
        "max_fmt": formatar_preco(stats.maximo),
        "media_fmt": formatar_preco(stats.media),
        "mediana_fmt": formatar_preco(stats.mediana),
        "iqr_min_fmt": formatar_preco(stats.iqr_min),
        "iqr_max_fmt": formatar_preco(stats.iqr_max),
    }


def _preparar_tabela(df: pd.DataFrame) -> tuple[List[Dict[str, str]], List[str]]:
    """
    Prepara dados do DataFrame para renderização em tabela HTML.

    Estratégia:
    - Seleciona colunas relevantes (quando disponíveis)
    - Ordena por preço (quando aplicável)
    - Formata valores (preço, datas, nulos)
    - Converte DataFrame em lista de dicionários

    Args:
        df: DataFrame já filtrado e tratado.

    Returns:
        Tuple contendo:
            - Lista de linhas (dict) para template
            - Lista de colunas exibidas
    """
    colunas_preferidas = [
        "Descrição do Item",
        "Cód. Catálogo",
        "Quantidade",
        "Preço Unitário (R$)",
        "Fornecedor",
        "UF",
        "Data da Compra",
    ]

    colunas = [c for c in colunas_preferidas if c in df.columns]

    df_ord = df.copy()

    # Ordenação por preço (melhor leitura para análise)
    if "Preço Unitário (R$)" in df_ord.columns:
        df_ord = df_ord.sort_values(by="Preço Unitário (R$)")
        df_ord["Preço Unitário (R$)"] = df_ord["Preço Unitário (R$)"].apply(formatar_preco)

    df_view = df_ord[colunas] if colunas else df_ord.head(100)

    linhas: List[Dict[str, str]] = []

    for _, row in df_view.iterrows():
        linha: Dict[str, str] = {}

        for col in colunas:
            val = row.get(col)

            if pd.isna(val):
                linha[col] = ""

            elif hasattr(val, "strftime"):
                linha[col] = val.strftime("%d / %m / %Y")

            else:
                linha[col] = str(val)

        linhas.append(linha)

    return linhas, colunas


def _store_one_time_payload(payload: Dict[str, Any]) -> str:
    """
    Armazena payload temporário para transporte entre requisições (PRG pattern).

    Args:
        payload: Dados a serem armazenados.

    Returns:
        Token único para recuperação.
    """
    token = uuid.uuid4().hex
    _ONE_TIME_COMPRAS[token] = payload

    # Controle simples de memória (FIFO)
    if len(_ONE_TIME_COMPRAS) > _ONE_TIME_MAX:
        _ONE_TIME_COMPRAS.pop(next(iter(_ONE_TIME_COMPRAS)), None)

    return token


@compras_bp.route("/", methods=["GET", "POST"])
def compras_index():
    """
    Endpoint principal para consulta de preços via Compras.gov.br (CATMAT).

    Fluxo (padrão PRG - Post/Redirect/Get):

    POST:
        - Recebe código CATMAT
        - Consulta API externa
        - Aplica limpeza e tratamento de dados
        - Calcula estatísticas
        - Prepara tabela para exibição
        - Armazena payload temporário
        - Redireciona para GET

    GET:
        - Recupera payload via token (uso único)
        - Renderiza template
        - Evita reenvio de formulário

    Returns:
        HTML renderizado com resultados e/ou mensagens de erro.
    """
    if request.method == "POST":
        erro: str | None = None
        codigo_item = (request.form.get("codigo_item") or "").strip()

        stats_view: Dict[str, Any] | None = None
        tabela_rows: List[Dict[str, str]] | None = None
        colunas_tabela: List[str] | None = None

        if not codigo_item:
            erro = "Informe o código do item (CATMAT)."

        else:
            try:
                logger.info("Consulta Compras.gov iniciada | codigo_item=%s", codigo_item)

                df = baixar_itens_catmat(codigo_item)

                if df.empty:
                    erro = (
                        "Nenhum registro retornado pela API do Compras.gov.br. "
                        "Verifique o código informado no Catálogo de Compras."
                    )
                else:
                    total_original = len(df)

                    stats, df_filtrado = processar_df(
                        df,
                        coluna_preco="Preço Unitário (R$)",
                    )

                    if stats is None or df_filtrado is None:
                        erro = (
                            "Nenhum registro permaneceu após os filtros de limpeza "
                            "(descrição, unidade, data e outliers)."
                        )
                    else:
                        stats_view = _build_stats_view(stats, total_original)
                        tabela_rows, colunas_tabela = _preparar_tabela(df_filtrado)

                logger.info(
                    "Consulta Compras.gov concluída | codigo_item=%s",
                    codigo_item,
                )

            except Exception:
                logger.exception("Erro na consulta Compras.gov | codigo_item=%s", codigo_item)
                erro = "Não foi possível processar a consulta no momento."

        token = _store_one_time_payload(
            {
                "erro": erro,
                "codigo_item": codigo_item,
                "stats": stats_view,
                "tabela_rows": tabela_rows or [],
                "colunas_tabela": colunas_tabela or [],
            }
        )

        return redirect(url_for("compras.compras_index", t=token))

    # --- GET ---
    token = (request.args.get("t") or "").strip()
    payload = _ONE_TIME_COMPRAS.pop(token, None) if token else None

    return render_template(
        "compras.html",
        aba_atual="compras",
        erro=(payload or {}).get("erro"),
        codigo_item=(payload or {}).get("codigo_item"),
        stats=(payload or {}).get("stats"),
        tabela_rows=(payload or {}).get("tabela_rows") or [],
        colunas_tabela=(payload or {}).get("colunas_tabela") or [],
    )