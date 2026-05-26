"""Settings de la API leídos vía pydantic-settings desde env + .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración runtime de la API.

    El esquema NO marca ANTHROPIC_API_KEY como required a nivel pydantic:
    la API debe iniciar incluso sin la key — en ese caso /extract responde
    503 y /health reporta `extractor_available=false`. Esto evita que un
    .env mal configurado bloquee el bootstrap completo.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key del clinical-extractor.",
    )
    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Tamaño máximo del PDF aceptado por POST /extract, en MB.",
    )
    # NoDecode evita que pydantic-settings intente JSON-decodear el env var
    # antes de pasarlo al validator. Render entrega ALLOWED_ORIGINS como CSV
    # (formato natural de la UI de env vars), no como JSON; sin NoDecode el
    # source EnvSettingsSource fallaría con SettingsError en Settings().
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description=(
            "Orígenes permitidos por CORS — match literal. "
            "Acepta CSV en env var (ALLOWED_ORIGINS=a,b,c). "
            "Para patrones (p. ej. *.vercel.app) usar allowed_origin_regex."
        ),
    )
    allowed_origin_regex: str | None = Field(
        # Default ancho para acomodar dev local + previews de Vercel + el dominio
        # de producción cuando se sepa. Refinar cuando exista dominio canónico.
        # TODO: reemplazar con regex específico del dominio de producción.
        default=(
            r"^https://([a-z0-9-]+\.)*vercel\.app$"
        ),
        description=(
            "Regex de orígenes permitidos por CORS. Útil para wildcards de "
            "Vercel preview deploys."
        ),
    )
    log_level: str = Field(
        default="INFO",
        description="Nivel de logging.",
    )

    # ---- Langfuse observability (opcional) -------------------------------
    # Mirror del setup en services/clinical-extractor/settings.py. La API
    # crea el trace padre del request HTTP; el extractor crea un generation
    # span como child del mismo trace (ver ADR 0007 § trace context).
    langfuse_public_key: str | None = Field(
        default=None,
        description="Langfuse public key (LANGFUSE_PUBLIC_KEY).",
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        description="Langfuse secret key (LANGFUSE_SECRET_KEY).",
    )
    langfuse_base_url: str = Field(
        default="https://us.cloud.langfuse.com",
        description="Endpoint del API de Langfuse Cloud (LANGFUSE_BASE_URL).",
    )
    langfuse_tracing_environment: str = Field(
        default="development",
        description=(
            "Tag de entorno (LANGFUSE_TRACING_ENVIRONMENT). Default 'development' "
            "es fail-safe: protege el dashboard 'production' de tests locales / "
            "CI que olviden setear la var. Render production setea esta env var "
            "explícitamente a 'production' en su Environment vars. Ver ADR 0007 "
            "§ actualización 2026-05-26 default environment."
        ),
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> object:
        """Parsea ALLOWED_ORIGINS desde env var (CSV) o desde código (list)."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def extractor_available(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def langfuse_enabled(self) -> bool:
        """True sólo si las 3 vars críticas están presentes y no vacías.

        Mirror de ``LangfuseSettings.enabled`` en clinical-extractor: el
        flag NO se setea como env var separada para evitar que un operador
        active observability sin tener credenciales (warnings en cada
        request).
        """
        return bool(
            self.langfuse_public_key
            and self.langfuse_secret_key
            and self.langfuse_base_url
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """FastAPI dependency: devuelve una instancia singleton de Settings."""
    return Settings()
