"""Tabla de pricing de Anthropic + cálculo de costo USD por extracción.

Estática a propósito (vs query a Anthropic billing API):

- Anthropic publica precios oficiales en https://www.anthropic.com/pricing
  y cambia ocasionalmente. Tener la tabla en código fuente hace que el
  cambio quede en commit log con review.
- Evita dependency adicional a la API de billing.
- ``calculate_cost_usd`` devuelve ``None`` para modelos no listados —
  el caller decide si registra cost=None o si lo trata como error.

Convención de unidades: precios en **USD por 1M tokens**. La función
divide internamente, así que el caller pasa tokens absolutos.

Cache pricing (prompt caching de Anthropic):

- ``cache_read`` se cobra a ~10% del precio de input → reduce costo en
  llamadas repetitivas con mismo prefijo.
- ``cache_write`` se cobra a ~125% del input por escribir al cache la
  primera vez.

Actualizar esta tabla cuando Anthropic cambie precios — referenciar el
PR del cambio en el commit message.
"""

from __future__ import annotations

# Precios USD por 1M tokens. Fuente: https://www.anthropic.com/pricing
# Snapshot tomado 2026-05-26. Actualizar manualmente cuando Anthropic
# publique cambios.
ANTHROPIC_PRICING_USD_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.0,
        "output": 15.0,
        "cache_read": 0.30,
        "cache_write": 3.75,
    },
    "claude-opus-4-7": {
        "input": 15.0,
        "output": 75.0,
        "cache_read": 1.50,
        "cache_write": 18.75,
    },
    "claude-haiku-4-5-20251001": {
        "input": 1.0,
        "output": 5.0,
        "cache_read": 0.10,
        "cache_write": 1.25,
    },
}


def calculate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float | None:
    """Calcula costo en USD a partir del token usage.

    Args:
        model: ID del modelo Anthropic. Si no está en la tabla, retorna ``None``.
        input_tokens: Tokens de input (no incluyen cache_read).
        output_tokens: Tokens de output.
        cache_read_tokens: Tokens leídos del prompt cache de Anthropic.
        cache_write_tokens: Tokens escritos al prompt cache.

    Returns:
        Costo total en USD redondeado a 6 decimales, o ``None`` si el
        modelo no está en la tabla de pricing. El caller decide cómo
        reportar el ``None`` (típicamente: tracear sin cost_details).

    Raises:
        Nada. Por diseño esta función no levanta — un modelo desconocido
        no debe romper el flujo de tracing.
    """
    pricing = ANTHROPIC_PRICING_USD_PER_1M_TOKENS.get(model)
    if pricing is None:
        return None

    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
        + (cache_read_tokens / 1_000_000) * pricing["cache_read"]
        + (cache_write_tokens / 1_000_000) * pricing["cache_write"]
    )
    return round(cost, 6)
