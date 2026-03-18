from __future__ import annotations


def formatar_preco(valor: float | None) -> str:
    """Formata um número como preço em reais no padrão brasileiro."""
    if valor is None:
        return "N/A"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

