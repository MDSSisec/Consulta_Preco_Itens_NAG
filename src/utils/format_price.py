from __future__ import annotations


def formatar_preco(valor: float | None) -> str:
    """
    Formata um valor numérico como moeda (Real - BRL) no padrão brasileiro.

    Exemplo:
        1234.56 → "R$ 1.234,56"
    """
    if valor is None:
        return "N/A"

    valor_formatado = f"{valor:,.2f}"
    valor_formatado = (
        valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
    )
    return f"R$ {valor_formatado}"
