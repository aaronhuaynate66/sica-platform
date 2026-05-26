"""Interface abstracta para LLM providers del clinical-extractor.

Define el contrato que cualquier provider concreto (Anthropic, Vertex AI
MedGemma/Gemini, OpenAI, etc.) debe cumplir.

Decisión de diseño: la abstracción es **síncrona** (``extract`` no es ``async``).
Razones:
- El extractor core no es async hoy; introducir async aquí obliga a un
  refactor más grande que no aporta valor inmediato.
- La concurrencia se maneja en el nivel batch del CLI (``asyncio.to_thread``
  envuelve la llamada síncrona en un thread).
- Cuando un provider necesite streaming async (R1+), agregaremos un método
  ``extract_async`` sin romper el contrato actual.

Decisión de diseño: ``ExtractionRequest`` lleva ``document_text`` (str), no
``pdf_bytes``. La extracción de texto del PDF es una capa anterior al provider
— el provider trabaja sobre texto plano. Esto deja la lógica de PDF en
``extractor.py`` y los providers reusables para inputs no-PDF.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from clinical_extractor.prompts import VersionedPrompt


class ProviderNotAvailableError(RuntimeError):
    """Provider configurado pero no operativo (env vars, GCP creds, etc.)."""


@dataclass(frozen=True)
class ExtractionRequest:
    """Input al provider para una extracción.

    Atributos:
        document_text: Texto plano del documento clínico (ya extraído del PDF).
        prompt: Prompt versionado a usar (system + user_template).
        model_id: Modelo concreto a invocar (debe estar en ``provider.supported_models``).
        max_tokens: Máximo de tokens de salida.
        max_retries: Reintentos en errores transitorios.
        initial_backoff: Espera inicial entre reintentos (segundos).
        max_backoff: Tope del backoff exponencial (segundos).
        timeout_seconds: Timeout por request al modelo.
        case_id: Identificador opcional del caso (típicamente el nombre del
            PDF sin extensión). Se propaga a Langfuse para que cada trace en
            el dashboard sea identificable. None desactiva el tag — el trace
            usa un fallback genérico.
        extra: Hooks específicos del provider (ej. ``{"region": "us-central1"}``
            para Vertex). Cada provider documenta qué claves espera.
    """

    document_text: str
    prompt: VersionedPrompt
    model_id: str
    max_tokens: int = 4096
    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 16.0
    timeout_seconds: float = 60.0
    case_id: str | None = None  # Identificador opcional para observability (Langfuse).
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionResponse:
    """Output del provider para una extracción.

    Atributos:
        parsed_output: Payload estructurado tal cual lo devolvió el modelo
            (dict listo para ``ObstetricSummary.model_validate``).
        input_tokens: Tokens de input cobrados/contados por el provider.
            ``None`` si el provider no reporta usage.
        output_tokens: Tokens de output. ``None`` si el provider no reporta.
        latency_ms: Latencia end-to-end de la llamada (incluyendo retries).
        model_used: ID exacto del modelo que respondió (eco del request).
        finish_reason: Razón de finalización si el provider la reporta
            (``tool_use``, ``end_turn``, ``max_tokens``, etc.). ``None`` si no aplica.
        retry_count: Cantidad de retries que se ejecutaron antes del éxito.
    """

    parsed_output: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    model_used: str
    finish_reason: str | None = None
    retry_count: int = 0


class LLMProvider(ABC):
    """Interface abstracta para providers de LLM.

    Cada provider concreto encapsula toda la lógica de:
    - Construcción del cliente (auth, timeouts).
    - Llamada al modelo con tool_use (ObstetricSummary schema).
    - Retry con backoff sobre errores transitorios.
    - Mapeo del output a ``ExtractionResponse``.

    El extractor core (``extractor.py``) selecciona el provider vía
    ``DEFAULT_REGISTRY.get_for_model(model_id)`` y delega la llamada.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """ID estable del provider: ``anthropic``, ``vertex-medgemma``, etc.

        Usado en telemetría y en el registry. Cambiarlo es ruptura de contrato
        — requiere ADR.
        """

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """Lista de ``model_id`` que este provider acepta en ``extract``.

        El registry usa esto para hacer ``get_for_model(model_id)``. Si un
        modelo aparece en dos providers (raro pero posible — ej. claude vía
        Bedrock vs API directa), gana el primero registrado.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """True si el provider está configurado y operativo en este entorno.

        Chequeo barato — sin red. Típicamente verifica presencia de env vars
        (``ANTHROPIC_API_KEY``, ``GOOGLE_APPLICATION_CREDENTIALS``, etc.).

        La API ``/models`` usa esto para indicar disponibilidad al frontend.
        """

    @abstractmethod
    def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Ejecuta una extracción.

        Maneja retry, timeout y errores internamente. Errores transitorios
        (red, 429, 5xx) se reintentan según la política del request. Errores
        del cliente (400/401/403/422) NO se reintentan — se propagan.

        Raises:
            ProviderNotAvailableError: si ``is_available()`` es False.
            ValueError: si ``request.model_id`` no está en ``supported_models``.
            ExtractionError: si los retries se agotan o el modelo no devuelve
                el tool_use esperado.
        """
