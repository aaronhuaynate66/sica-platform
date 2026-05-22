"""Tests del módulo settings — foco en parseo de ALLOWED_ORIGINS desde env.

Regression: en pydantic-settings 2.x, los campos de tipo `list[str]` son
JSON-decoded en EnvSettingsSource ANTES de invocar field_validator(mode="before").
Esto rompió el deploy a Render que entrega ALLOWED_ORIGINS como CSV. El fix
usa `Annotated[list[str], NoDecode]` para suprimir ese paso de JSON-decode.

Estos tests congelan el contrato: ALLOWED_ORIGINS en env como CSV debe
parsearse a list[str] limpiamente, sin tropezar con JSON.
"""

from __future__ import annotations

import pytest

from sica_api.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_get_settings_cache():
    """Cada test debe construir un Settings fresco; el LRU cache contamina."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_allowed_origins_parses_csv_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "a.com,b.com,c.com")
    s = Settings()
    assert s.allowed_origins == ["a.com", "b.com", "c.com"]


def test_allowed_origins_trims_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render UI a veces pega valores con espacios extra; deben caer limpios."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "a.com,  b.com , c.com   ")
    s = Settings()
    assert s.allowed_origins == ["a.com", "b.com", "c.com"]


def test_allowed_origins_handles_render_real_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valor exacto que pusimos en Render — antes del fix esto reventaba."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://sica-web.vercel.app,https://*.vercel.app,http://localhost:3000",
    )
    s = Settings()
    assert s.allowed_origins == [
        "https://sica-web.vercel.app",
        "https://*.vercel.app",
        "http://localhost:3000",
    ]


def test_allowed_origins_skips_empty_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comas finales o dobles no deben generar strings vacíos."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "a.com,,b.com,")
    s = Settings()
    assert s.allowed_origins == ["a.com", "b.com"]


def test_allowed_origins_uses_default_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    s = Settings()
    assert s.allowed_origins == ["http://localhost:3000"]


def test_allowed_origins_accepts_python_list_directly() -> None:
    """Cuando se construye desde código (no env), la lista debe pasar tal cual."""
    s = Settings(allowed_origins=["x.com", "y.com"])  # type: ignore[arg-type]
    assert s.allowed_origins == ["x.com", "y.com"]


def test_allowed_origins_empty_string_resolves_to_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ALLOWED_ORIGINS='' en env produce []; el regex sigue cubriendo *.vercel.app."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    s = Settings()
    assert s.allowed_origins == []
