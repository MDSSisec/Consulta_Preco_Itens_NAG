from __future__ import annotations


def formatar_preco(valor: float | None) -> str:
    """
    Formata um valor numérico como moeda (Real - BRL) no padrão brasileiro.

    Exemplo:
        1234.56 → "R$ 1.234,56"

    Estratégia:
        - Utiliza formatação padrão do Python (en_US) como base:
            1,234.56
        - Realiza substituição manual para padrão pt-BR:
            milhar (,) → .
            decimal (.) → ,
        - Usa placeholder intermediário para evitar conflito na substituição

    Regras:
        - None → "N/A"
        - Mantém sempre 2 casas decimais
        - Prefixo fixo "R$"

    Args:
        valor: Número a ser formatado (float) ou None.

    Returns:
        String formatada no padrão monetário brasileiro.
    """
    if valor is None:
        return "N/A"

    # Formatação base (padrão US: 1,234.56)
    valor_formatado = f"{valor:,.2f}"

    # Conversão para padrão BR:
    # 1.234,56
    valor_formatado = (
        valor_formatado
        .replace(",", "X")  # protege separador de milhar
        .replace(".", ",")  # troca decimal
        .replace("X", ".")  # restaura milhar
    )

    return f"R$ {valor_formatado}"