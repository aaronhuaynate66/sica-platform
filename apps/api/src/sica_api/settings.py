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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """FastAPI dependency: devuelve una instancia singleton de Settings."""
    return Settings()
