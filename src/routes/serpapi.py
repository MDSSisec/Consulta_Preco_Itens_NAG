from __future__ import annotations

import logging
import statistics
import uuid
from typing import Any, Dict

from flask import Blueprint, redirect, render_template, request, url_for

from src.core.formatting import formatar_preco
from src.services.serpapi_client import buscar_google_shopping


logger = logging.getLogger(__name__)

serpapi_bp = Blueprint("serpapi", __name__)

# Armazenamento temporário (in-memory) para transporte de estado entre POST → GET.
# Evita reenvio de formulário (pattern PRG: Post/Redirect/Get).
_ONE_TIME_SERPAPI: Dict[str, Dict[str, Any]] = {}

# Limite máximo de itens armazenados para evitar crescimento descontrolado em memória.
_ONE_TIME_MAX = 20


def _calcular_estatisticas(resultados: list[Dict[str, Any]]) -> Dict[str, Any] | None:
    """
    Calcula estatísticas descritivas a partir dos preços numéricos dos resultados.

    Estratégia:
    - Filtra apenas valores válidos (numéricos e positivos)
    - Calcula métricas robustas para análise de preços
    - Utiliza mediana e IQR para reduzir impacto de outliers

    Args:
        resultados: Lista de itens retornados pela SerpAPI.

    Returns:
        Dicionário formatado para a camada de apresentação ou None se não houver dados válidos.
    """
    precos = [
        r["numeric_price"]
        for r in resultados
        if isinstance(r.get("numeric_price"), (int, float)) and r["numeric_price"] > 0
    ]

    if not precos:
        return None

    precos_sorted = sorted(precos)

    minimo = min(precos_sorted)
    maximo = max(precos_sorted)
    media = statistics.mean(precos_sorted)
    mediana = statistics.median(precos_sorted)

    # Cálculo manual de quartis (compatível com listas pequenas)
    q1 = statistics.median(precos_sorted[: len(precos_sorted) // 2])
    q3 = statistics.median(precos_sorted[(len(precos_sorted) + 1) // 2 :])

    return {
        "n_registros_validos": len(precos_sorted),
        "n_registros_totais": len(resultados),
        "min_fmt": formatar_preco(minimo),
        "max_fmt": formatar_preco(maximo),
        "media_fmt": formatar_preco(media),
        "mediana_fmt": formatar_preco(mediana),
        "iqr_min_fmt": formatar_preco(q1),
        "iqr_max_fmt": formatar_preco(q3),
    }


def _formatar_precos(resultados: list[Dict[str, Any]]) -> None:
    """
    Aplica formatação monetária nos preços válidos diretamente na lista de resultados.

    Observação:
    - Mantém o campo `numeric_price` para cálculos
    - Sobrescreve `price` apenas para exibição

    Args:
        resultados: Lista de resultados a ser modificada (in-place).
    """
    for item in resultados:
        np = item.get("numeric_price")
        if isinstance(np, (int, float)) and np > 0:
            item["price"] = formatar_preco(float(np))


def _store_one_time_payload(payload: Dict[str, Any]) -> str:
    """
    Armazena payload temporário para uso único (padrão PRG).

    Estratégia:
    - Gera token único
    - Armazena payload em memória
    - Remove itens antigos quando excede limite

    Args:
        payload: Dados a serem armazenados.

    Returns:
        Token único para recuperação posterior.
    """
    token = uuid.uuid4().hex
    _ONE_TIME_SERPAPI[token] = payload

    # Controle simples de memória (FIFO baseado em ordem de inserção)
    if len(_ONE_TIME_SERPAPI) > _ONE_TIME_MAX:
        _ONE_TIME_SERPAPI.pop(next(iter(_ONE_TIME_SERPAPI)), None)

    return token


@serpapi_bp.route("/serpapi", methods=["GET", "POST"])
def serpapi_index():
    """
    Endpoint principal para consulta de preços via SerpAPI.

    Fluxo (padrão PRG - Post/Redirect/Get):

    POST:
        - Recebe termo de busca
        - Consulta API externa
        - Processa resultados e estatísticas
        - Armazena payload temporário
        - Redireciona para GET com token

    GET:
        - Recupera payload via token (uso único)
        - Renderiza template com dados
        - Evita reenvio de formulário ao recarregar página

    Returns:
        HTML renderizado com resultados, estatísticas e possíveis mensagens de erro.
    """
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

                resultados = buscar_google_shopping(termo, num=num)

                _formatar_precos(resultados)
                stats_view = _calcular_estatisticas(resultados)

                logger.info(
                    "Consulta SerpAPI concluída | termo=%s | resultados=%d",
                    termo,
                    len(resultados),
                )

            except Exception as exc:
                logger.exception("Erro na consulta SerpAPI | termo=%s", termo)
                erro = "Não foi possível realizar a consulta no momento."

        token = _store_one_time_payload(
            {
                "erro": erro,
                "termo": termo,
                "num": num,
                "stats": stats_view,
                "resultados": resultados,
            }
        )

        return redirect(url_for("serpapi.serpapi_index", t=token))

    # --- GET ---
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