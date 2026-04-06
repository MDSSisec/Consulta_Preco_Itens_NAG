from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from flask import Blueprint, redirect, render_template, request, url_for

from src.services.compras_gov_service import fetch_compras_gov
from src.services.serp_api_service import fetch_google_shopping
from src.services.price_service import (
    build_compras_stats_view,
    calcular_estatisticas_serpapi,
    formatar_precos_serpapi,
    preparar_tabela_compras,
    processar_df,
)


logger = logging.getLogger(__name__)

compras_bp = Blueprint("compras", __name__)

_ONE_TIME_COMPRAS: Dict[str, Dict[str, Any]] = {}
_ONE_TIME_MAX = 20


def _store_one_time_compras(payload: Dict[str, Any]) -> str:
    token = uuid.uuid4().hex
    _ONE_TIME_COMPRAS[token] = payload
    if len(_ONE_TIME_COMPRAS) > _ONE_TIME_MAX:
        _ONE_TIME_COMPRAS.pop(next(iter(_ONE_TIME_COMPRAS)), None)
    return token


@compras_bp.route("/", methods=["GET", "POST"])
def compras_index():
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

                df = fetch_compras_gov(codigo_item)

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
                        stats_view = build_compras_stats_view(stats, total_original)
                        tabela_rows, colunas_tabela = preparar_tabela_compras(df_filtrado)

                logger.info(
                    "Consulta Compras.gov concluída | codigo_item=%s",
                    codigo_item,
                )

            except Exception:
                logger.exception("Erro na consulta Compras.gov | codigo_item=%s", codigo_item)
                erro = "Não foi possível processar a consulta no momento."

        token = _store_one_time_compras(
            {
                "erro": erro,
                "codigo_item": codigo_item,
                "stats": stats_view,
                "tabela_rows": tabela_rows or [],
                "colunas_tabela": colunas_tabela or [],
            }
        )

        return redirect(url_for("compras.compras_index", t=token))

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


serpapi_bp = Blueprint("serpapi", __name__)

_ONE_TIME_SERPAPI: Dict[str, Dict[str, Any]] = {}


def _store_one_time_serpapi(payload: Dict[str, Any]) -> str:
    token = uuid.uuid4().hex
    _ONE_TIME_SERPAPI[token] = payload
    if len(_ONE_TIME_SERPAPI) > _ONE_TIME_MAX:
        _ONE_TIME_SERPAPI.pop(next(iter(_ONE_TIME_SERPAPI)), None)
    return token


@serpapi_bp.route("/serpapi", methods=["GET", "POST"])
def serpapi_index():
    if request.method == "POST":
        erro: str | None = None
        termo = (request.form.get("q") or "").strip()
        num_raw = (request.form.get("num") or "").strip()
        num = 60
        if num_raw:
            try:
                num = int(num_raw)
            except ValueError:
                num = 60
        num = max(1, min(num, 100))

        resultados: list[Dict[str, Any]] = []
        stats_view: Dict[str, Any] | None = None

        if not termo:
            erro = "Informe um termo para busca."
        else:
            try:
                logger.info("Consulta SerpAPI iniciada | termo=%s", termo)

                resultados = fetch_google_shopping(termo, num=num)

                formatar_precos_serpapi(resultados)
                stats_view = calcular_estatisticas_serpapi(resultados)

                logger.info(
                    "Consulta SerpAPI concluída | termo=%s | resultados=%d",
                    termo,
                    len(resultados),
                )

            except Exception:
                logger.exception("Erro na consulta SerpAPI | termo=%s", termo)
                erro = "Não foi possível realizar a consulta no momento."

        token = _store_one_time_serpapi(
            {
                "erro": erro,
                "termo": termo,
                "num": num,
                "stats": stats_view,
                "resultados": resultados,
            }
        )

        return redirect(url_for("serpapi.serpapi_index", t=token))

    token = (request.args.get("t") or "").strip()
    payload = _ONE_TIME_SERPAPI.pop(token, None) if token else None

    return render_template(
        "serpapi.html",
        aba_atual="serpapi",
        erro=(payload or {}).get("erro"),
        termo=(payload or {}).get("termo"),
        num=(payload or {}).get("num"),
        stats=(payload or {}).get("stats"),
        resultados=(payload or {}).get("resultados") or [],
    )
