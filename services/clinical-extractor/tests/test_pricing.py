"""Tests de ``clinical_extractor.pricing``.

Cubren:
- Cálculo correcto para sonnet 4.5 sin cache.
- Cálculo correcto con cache_read (descuento ~10x).
- Cálculo correcto con cache_write (recargo ~25%).
- ``None`` para modelo desconocido (no levanta).
- Cero tokens devuelve 0.0.
- Cálculo para opus y haiku (sanity coverage de los 3 modelos).
"""

from __future__ import annotations

import pytest

from clinical_extractor.pricing import (
    ANTHROPIC_PRICING_USD_PER_1M_TOKENS,
    calculate_cost_usd,
)

SONNET = "claude-sonnet-4-5-20250929"
OPUS = "claude-opus-4-7"
HAIKU = "claude-haiku-4-5-20251001"


def test_sonnet_without_cache() -> None:
    # 1000 input + 500 output = 1000/1M * 3 + 500/1M * 15 = 0.003 + 0.0075 = 0.0105
    cost = calculate_cost_usd(SONNET, input_tokens=1000, output_tokens=500)
    assert cost == pytest.approx(0.0105, abs=1e-6)


def test_sonnet_with_cache_read_reduces_cost() -> None:
    # Sin cache: 100_000 input = 0.30 USD. Con cache_read: 100_000 cache = 0.03 USD.
    no_cache = calculate_cost_usd(SONNET, input_tokens=100_000, output_tokens=0)
    with_cache = calculate_cost_usd(
        SONNET, input_tokens=0, output_tokens=0, cache_read_tokens=100_000
    )
    assert no_cache == pytest.approx(0.30, abs=1e-6)
    assert with_cache == pytest.approx(0.03, abs=1e-6)
    # Cache read es 10x mas barato que input.
    assert no_cache is not None and with_cache is not None
    assert no_cache > with_cache * 9


def test_sonnet_with_cache_write_increases_cost() -> None:
    # cache_write = 3.75 USD/1M → 100k tokens = 0.375 USD (más caro que input 0.30).
    cost = calculate_cost_usd(
        SONNET,
        input_tokens=0,
        output_tokens=0,
        cache_write_tokens=100_000,
    )
    assert cost == pytest.approx(0.375, abs=1e-6)


def test_unknown_model_returns_none() -> None:
    cost = calculate_cost_usd("not-a-real-model", input_tokens=1000, output_tokens=500)
    assert cost is None


def test_zero_tokens_returns_zero() -> None:
    cost = calculate_cost_usd(SONNET, input_tokens=0, output_tokens=0)
    assert cost == 0.0


def test_opus_pricing_is_higher_than_sonnet() -> None:
    sonnet = calculate_cost_usd(SONNET, input_tokens=1000, output_tokens=500)
    opus = calculate_cost_usd(OPUS, input_tokens=1000, output_tokens=500)
    assert sonnet is not None and opus is not None
    # opus es ~5x mas caro que sonnet en pricing per-token.
    assert opus > sonnet * 4


def test_haiku_pricing_is_lower_than_sonnet() -> None:
    sonnet = calculate_cost_usd(SONNET, input_tokens=1000, output_tokens=500)
    haiku = calculate_cost_usd(HAIKU, input_tokens=1000, output_tokens=500)
    assert sonnet is not None and haiku is not None
    # haiku es ~1/3 de sonnet.
    assert haiku < sonnet / 2


def test_pricing_table_has_required_keys_per_model() -> None:
    """Sanity: cada entrada de la tabla tiene los 4 campos requeridos."""
    required = {"input", "output", "cache_read", "cache_write"}
    for model, pricing in ANTHROPIC_PRICING_USD_PER_1M_TOKENS.items():
        assert required.issubset(pricing.keys()), (
            f"Modelo {model} carece de algún campo en la tabla: {pricing.keys()}"
        )
        for k, v in pricing.items():
            assert v > 0, f"{model}.{k} debe ser > 0, es {v}"


def test_cost_rounded_to_six_decimals() -> None:
    """Costo se redondea a 6 decimales — útil para serializar a Langfuse sin ruido."""
    # 1 token de input en sonnet = 3e-6 USD
    cost = calculate_cost_usd(SONNET, input_tokens=1, output_tokens=0)
    assert cost is not None
    # Verificar que tiene como máximo 6 decimales significativos.
    assert cost == round(cost, 6)
