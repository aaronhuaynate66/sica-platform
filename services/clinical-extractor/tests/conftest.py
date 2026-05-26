"""Fixtures comunes para todos los tests del clinical-extractor.

**Crítico — aislamiento de Langfuse en tests:**

Con tracing habilitado en ``AnthropicProvider.extract``, cualquier test
que invoque ``provider.extract()`` con un cliente Anthropic mockeado
**también** intentará llamar a ``trace_extraction``. Si el cwd contiene
un ``.env`` con credenciales reales de Langfuse, los tests mandarían
traces reales al server — contaminando el dashboard con runs sintéticos.

La fixture ``_isolate_tracing_env`` (autouse) garantiza que:

1. Cada test corre con ``cwd = tmp_path`` (sin ``.env``).
2. Los caches de ``get_langfuse_settings`` y ``get_langfuse_client``
   se limpian antes y después.
3. Resultado: ``LangfuseSettings.enabled`` es ``False`` para todos los
   tests por default. ``get_langfuse_client()`` retorna ``None``.
   ``trace_extraction()`` se vuelve no-op silencioso.

Tests que quieran simular Langfuse habilitado deben usar
``monkeypatch.setenv`` + patching del SDK explícitamente (ver
``test_tracing.py``).
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_tracing_env(monkeypatch, tmp_path):
    """Aísla cada test del .env real del paquete + limpia caches."""
    from clinical_extractor import tracing
    from clinical_extractor.settings import get_langfuse_settings

    monkeypatch.chdir(tmp_path)
    # Belt-and-suspenders: incluso si hay env vars en el environment
    # del CI, las borramos para que ningún test toque Langfuse real.
    for var in (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_SAMPLE_RATE",
        "LANGFUSE_TRACING_ENVIRONMENT",
    ):
        monkeypatch.delenv(var, raising=False)
    tracing.get_langfuse_client.cache_clear()
    get_langfuse_settings.cache_clear()
    yield
    tracing.get_langfuse_client.cache_clear()
    get_langfuse_settings.cache_clear()
