from __future__ import annotations

import uuid

import pandas as pd
from flask import Blueprint, redirect, render_template, request, url_for

from src.core.cleaning import processar_df
from src.core.formatting import formatar_preco
from src.services.compras_gov import baixar_itens_catmat

compras_bp = Blueprint("compras", __name__)

_ONE_TIME_COMPRAS: dict[str, dict] = {}
_ONE_TIME_MAX = 20


@compras_bp.route("/", methods=["GET", "POST"])
def compras_index():
    if request.method == "POST":
        erro = None
        codigo_item = None
        stats_view = None
        tabela_rows = None
        colunas_tabela = None

        codigo_item = (request.form.get("codigo_item") or "").strip()
        if not codigo_item:
            erro = "Informe o código do item (CATMAT)."
        else:
            try:
                df = baixar_itens_catmat(codigo_item)
                if df.empty:
                    erro = (
                        "Nenhum registro retornado pela API do Compras.gov.br para esse código. "
                        "Verifique se o código está correto no Catálogo de Compras."
                    )
                else:
                    total_original = len(df)
                    stats, df_filtrado = processar_df(df, coluna_preco="Preço Unitário (R$)")
                    if stats is None or df_filtrado is None:
                        erro = (
                            "Nenhum registro permaneceu após os filtros de limpeza "
                            "(descrição, unidade, data e outliers)."
                        )
                    else:
                        stats_view = {
                            "n_registros_validos": stats.n_registros,
                            "n_registros_totais": total_original,
                            "min_fmt": formatar_preco(stats.minimo),
                            "max_fmt": formatar_preco(stats.maximo),
                            "media_fmt": formatar_preco(stats.media),
                            "mediana_fmt": formatar_preco(stats.mediana),
                            "iqr_min_fmt": formatar_preco(stats.iqr_min),
                            "iqr_max_fmt": formatar_preco(stats.iqr_max),
                        }

                        colunas_preferidas = [
                            "Descrição do Item",
                            "Cód. Catálogo",
                            "Quantidade",
                            "Preço Unitário (R$)",
                            "Fornecedor",
                            "UF",
                            "Data da Compra",
                        ]
                        cols = [c for c in colunas_preferidas if c in df_filtrado.columns]
                        colunas_tabela = cols

                        df_ord = df_filtrado.copy()
                        if "Preço Unitário (R$)" in df_ord.columns:
                            df_ord = df_ord.sort_values(by="Preço Unitário (R$)")
                            df_ord["Preço Unitário (R$)"] = df_ord["Preço Unitário (R$)"].apply(formatar_preco)

                        df_view = df_ord[cols] if cols else df_ord.head(100)

                        tabela_rows = []
                        for _, row in df_view.iterrows():
                            r = {}
                            for c in colunas_tabela:
                                val = row.get(c)
                                if pd.isna(val):
                                    r[c] = ""
                                elif hasattr(val, "strftime"):
                                    r[c] = val.strftime("%d / %m / %Y")
                                else:
                                    r[c] = str(val)
                            tabela_rows.append(r)
            except Exception as e:
                erro = f"Erro ao consultar/processar Compras.gov.br: {e}"

        token = uuid.uuid4().hex
        _ONE_TIME_COMPRAS[token] = {
            "erro": erro,
            "codigo_item": codigo_item,
            "stats": stats_view,
            "tabela_rows": tabela_rows or [],
            "colunas_tabela": colunas_tabela or [],
        }
        if len(_ONE_TIME_COMPRAS) > _ONE_TIME_MAX:
            _ONE_TIME_COMPRAS.pop(next(iter(_ONE_TIME_COMPRAS)), None)
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

