"""Provider Vertex AI MedGemma — stub.

Esqueleto del provider para MedGemma 4B servido desde Vertex AI / GKE.
La implementación concreta del método ``extract`` se completa cuando haya
GCP credentials configurados (ver issue #12 — viabilidad MedGemma 4B local
en el entorno del partner).

Diseño esperado del thursday session:
- Cliente: ``google.cloud.aiplatform`` o llamada directa a endpoint REST de
  Vertex Prediction.
- Auth: Application Default Credentials (``GOOGLE_APPLICATION_CREDENTIALS``
  apuntando a service account JSON, o ``gcloud auth application-default
  login`` para dev).
- Schema: forzar JSON output vía constrained decoding o prompt engineering
  (MedGemma 4B no tiene tool_use nativo como Claude).
- Retry: misma política que AnthropicProvider — exponencial con jitter.
- Audit trail: integrar con ``telemetry.emit`` igual que Anthropic.

Variables de entorno esperadas (a confirmar en thursday):
- ``GOOGLE_APPLICATION_CREDENTIALS`` — path al service account JSON.
- ``GCP_PROJECT`` — project ID del partner.
- ``GCP_REGION`` — región Vertex (default us-central1).
- ``MEDGEMMA_ENDPOINT_ID`` — endpoint deployment ID en Vertex.

Ver ADR 0004 Nivel 1 para el rol de MedGemma 4B en la política de routing
de SICA (default para resumen obstétrico cuando #12 cierre con verde).
"""

from __future__ import annotations

import os

from clinical_extractor.providers.base import (
    ExtractionRequest,
    ExtractionResponse,
    LLMProvider,
)


class VertexMedGemmaProvider(LLMProvider):
    """Provider MedGemma 4B vía Vertex AI — stub, no implementado.

    Devuelve ``is_available() == False`` hasta que las env vars de GCP estén
    presentes Y el método ``extract`` esté implementado. Llamar a ``extract``
    en este estado levanta ``NotImplementedError`` con mensaje claro.
    """

    _PROVIDER_ID = "vertex-medgemma"
    _SUPPORTED_MODELS = ("medgemma-4b-it",)

    # Env vars que la implementación real va a requerir. Hoy se chequean
    # solo para hacer ``is_available()`` honesto: si no están todas, el
    # provider no está listo.
    _REQUIRED_ENV_VARS = (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCP_PROJECT",
        "MEDGEMMA_ENDPOINT_ID",
    )

    @property
    def provider_id(self) -> str:
        return self._PROVIDER_ID

    @property
    def supported_models(self) -> list[str]:
        return list(self._SUPPORTED_MODELS)

    def is_available(self) -> bool:
        # En este stub, is_available() es siempre False — la lógica de chequeo
        # de env vars vive aquí para que el día que extract() esté implementado
        # solo haya que invertir este return.
        env_ok = all(os.getenv(v) for v in self._REQUIRED_ENV_VARS)
        if not env_ok:
            return False
        # Aun con env vars presentes, el provider no está operativo hasta que
        # extract() se implemente. Cuando se complete, eliminar este flag.
        return False

    def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        # TODO(#12): implementar llamada real a Vertex AI MedGemma 4B.
        #
        # Pseudocódigo del thursday:
        #
        #   from google.cloud import aiplatform
        #   aiplatform.init(project=os.environ["GCP_PROJECT"],
        #                   location=os.environ.get("GCP_REGION", "us-central1"))
        #   endpoint = aiplatform.Endpoint(os.environ["MEDGEMMA_ENDPOINT_ID"])
        #
        #   prompt_text = request.prompt.system + "\n\n" + \
        #       request.prompt.user_template.format(document_text=request.document_text)
        #
        #   # MedGemma no tiene tool_use → forzar JSON estructurado vía prompt
        #   # + parsing defensivo en el output.
        #   prediction = endpoint.predict(instances=[{"prompt": prompt_text,
        #                                             "max_tokens": request.max_tokens}])
        #
        #   raw_text = prediction.predictions[0]
        #   parsed = _parse_json_strict(raw_text)  # raise si no parsea
        #
        #   return ExtractionResponse(
        #       parsed_output=parsed,
        #       input_tokens=None,  # Vertex no reporta usage uniformemente
        #       output_tokens=None,
        #       latency_ms=...,
        #       model_used=request.model_id,
        #       finish_reason="json",
        #       retry_count=...,
        #   )
        msg = (
            "VertexMedGemmaProvider.extract no está implementado. "
            "Pendiente sesión con GCP credentials (issue #12). "
            "Mientras tanto, usar provider 'anthropic' con un modelo Claude."
        )
        raise NotImplementedError(msg)
