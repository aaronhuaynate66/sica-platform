"""Settings runtime del clinical-extractor (Langfuse + futuros).

Diseño:

- ``LangfuseSettings`` lee las env vars ``LANGFUSE_*`` desde ``.env``
  + entorno. La instancia singleton se obtiene vía ``get_langfuse_settings()``
  (cached con ``lru_cache``) — el chequeo de presencia de credenciales corre
  una sola vez por proceso.

- **``enabled`` no se setea desde env var**: se computa como property a
  partir de la presencia de las 3 vars críticas (``public_key``,
  ``secret_key``, ``base_url``). Esto evita que un operador active el flag
  manualmente sin tener las credenciales — el tracing arrancaría a
  fallar silenciosamente.

- Si ``enabled`` es ``False``, el código de ``tracing.py`` cae a no-op.

Por qué este módulo no vive junto a sica-api: el extractor es la unidad
que invoca al modelo; mantener la config de observability acoplada al
extractor evita acoplamientos al API (apps/api consume este paquete).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LangfuseSettings(BaseSettings):
    """Configuración de tracing Langfuse leída desde env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LANGFUSE_",
        case_sensitive=False,
        extra="ignore",
    )

    public_key: str | None = Field(
        default=None,
        description="Langfuse public key (LANGFUSE_PUBLIC_KEY).",
    )
    secret_key: str | None = Field(
        default=None,
        description="Langfuse secret key (LANGFUSE_SECRET_KEY).",
    )
    base_url: str = Field(
        default="https://us.cloud.langfuse.com",
        description="Endpoint del API de Langfuse Cloud (LANGFUSE_BASE_URL).",
    )
    sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Fracción de extracciones a trazar (LANGFUSE_SAMPLE_RATE). "
            "1.0 = trazar todas; 0.1 = 10%. Tracing es barato (~50ms overhead) "
            "pero se puede reducir en R2+ si el volumen crece."
        ),
    )
    tracing_environment: str = Field(
        default="production",
        description=(
            "Tag de entorno para separar prod/staging/dev en el dashboard "
            "(LANGFUSE_TRACING_ENVIRONMENT). En CI override a 'ci' o 'test'."
        ),
    )

    @property
    def enabled(self) -> bool:
        """True sólo si las 3 vars críticas están presentes y no vacías.

        ``base_url`` tiene default no vacío así que en la práctica el flag
        depende de ``public_key`` y ``secret_key``. Lo dejamos chequeado
        explícito por simetría — si alguien setea ``LANGFUSE_BASE_URL=""``
        a mano, el flag debe responder False también.
        """
        return bool(self.public_key) and bool(self.secret_key) and bool(self.base_url)


@lru_cache(maxsize=1)
def get_langfuse_settings() -> LangfuseSettings:
    """Singleton — el chequeo del entorno corre una sola vez por proceso."""
    return LangfuseSettings()
