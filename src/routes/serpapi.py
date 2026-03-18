from __future__ import annotations

import statistics
import uuid
from typing import Any, Dict

from flask import Blueprint, redirect, render_template, request, url_for

from src.core.formatting import formatar_preco
from src.services.serpapi_client import buscar_google_shopping

serpapi_bp = Blueprint("serpapi", __name__)

_ONE_TIME_SERPAPI: Dict[str, Dict[str, Any]] = {}
_ONE_TIME_MAX = 20


@serpapi_bp.route("/serpapi", methods=["GET", "POST"])
def serpapi_index():
    if request.method == "POST":
        erro = None
        termo = (request.form.get("q") or "").strip()
        resultados = []
        stats_view = None

        if not termo:
            erro = "Informe um termo para buscar na SerpAPI."
        else:
            try:
                resultados = buscar_google_shopping(termo)
                for r in resultados:
                    np = r.get("numeric_price")
                    if isinstance(np, (int, float)) and np > 0:
                        r["price"] = formatar_preco(float(np))
                precos = [
                    r["numeric_price"]
                    for r in resultados
                    if isinstance(r.get("numeric_price"), (int, float)) and r["numeric_price"] > 0
                ]
                if precos:
                    precos_sorted = sorted(precos)
                    minimo = min(precos_sorted)
                    maximo = max(precos_sorted)
                    media = statistics.mean(precos_sorted)
                    mediana = statistics.median(precos_sorted)
                    q1 = statistics.median(precos_sorted[: len(precos_sorted) // 2])
                    q3 = statistics.median(precos_sorted[(len(precos_sorted) + 1) // 2 :])

                    stats_view = {
                        "n_registros_validos": len(precos_sorted),
                        "n_registros_totais": len(resultados),
                        "min_fmt": formatar_preco(minimo),
                        "max_fmt": formatar_preco(maximo),
                        "media_fmt": formatar_preco(media),
                        "mediana_fmt": formatar_preco(mediana),
                        "iqr_min_fmt": formatar_preco(q1),
                        "iqr_max_fmt": formatar_preco(q3),
                    }
            except Exception as e:
                erro = f"Erro ao consultar a SerpAPI: {e}"

        token = uuid.uuid4().hex
        _ONE_TIME_SERPAPI[token] = {
            "erro": erro,
            "termo": termo,
            "stats": stats_view,
            "resultados": resultados,
        }
        if len(_ONE_TIME_SERPAPI) > _ONE_TIME_MAX:
            # Remove um item antigo (ordem de inserção do dict)
            _ONE_TIME_SERPAPI.pop(next(iter(_ONE_TIME_SERPAPI)), None)
        # Redireciona para GET: ao recarregar, a página zera (token é consumido uma vez).
        return redirect(url_for("serpapi.serpapi_index", t=token))

    token = (request.args.get("t") or "").strip()
    payload = _ONE_TIME_SERPAPI.pop(token, None) if token else None

    return render_template(
        "serpapi.html",
        aba_atual="serpapi",
        erro=(payload or {}).get("erro"),
        termo=(payload or {}).get("termo"),
        stats=(payload or {}).get("stats"),
        resultados=(payload or {}).get("resultados") or [],
    )

