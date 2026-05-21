"""Lógica core del clinical-extractor: PDF → ObstetricSummary."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, cast

import anthropic
import pypdf
from pydantic import ValidationError

from clinical_extractor.prompts import VersionedPrompt, get_active_prompt
from clinical_extractor.schemas import ObstetricSummary

if TYPE_CHECKING:
    from pathlib import Path

    from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 60.0

TOOL_NAME = "record_obstetric_summary"


class ExtractionError(RuntimeError):
    """Error en la pipeline de extracción.

    Cualquier fallo (PDF ilegible, modelo no devolvió tool_use, validación
    Pydantic falló, etc.) se levanta como esta excepción con contexto.
    """


def _read_pdf_text(pdf_path: Path) -> str:
    """Extrae texto plano de un PDF nativo con pypdf.

    Para PDFs escaneados sin capa de texto, esto devuelve string vacío o
    fragmentos sueltos — caso en el cual habría que enrutar a OCR (no en R0).
    """
    if not pdf_path.exists():
        msg = f"PDF no existe: {pdf_path}"
        raise ExtractionError(msg)

    if pdf_path.suffix.lower() != ".pdf":
        msg = f"Archivo no es PDF: {pdf_path}"
        raise ExtractionError(msg)

    try:
        reader = pypdf.PdfReader(str(pdf_path))
    except Exception as exc:
        msg = f"No se pudo leer el PDF {pdf_path}: {exc}"
        raise ExtractionError(msg) from exc

    pages_text: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            msg = f"Error extrayendo texto de página {i}: {exc}"
            raise ExtractionError(msg) from exc
        pages_text.append(f"[Página {i}]\n{text}")

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        msg = (
            f"El PDF {pdf_path} no devolvió texto extraíble. "
            "Puede ser un PDF escaneado sin capa de texto — requiere OCR (fuera de scope R0)."
        )
        raise ExtractionError(msg)
    return full_text


def _build_extraction_tool() -> ToolParam:
    """Construye el tool spec para Anthropic basado en el schema de ObstetricSummary.

    Usamos tool use (en vez de instrucción "devolvé JSON") porque garantiza
    structured output validado por el modelo antes de devolverlo, y porque
    nos permite indicar explícitamente qué herramienta queremos que invoque.
    """
    schema = ObstetricSummary.model_json_schema()
    tool: ToolParam = {
        "name": TOOL_NAME,
        "description": (
            "Registra el resumen estructurado de la historia clínica obstétrica "
            "extraído del documento. Llamar exactamente una vez."
        ),
        "input_schema": cast("Any", schema),
    }
    return tool


def _call_model(
    *,
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    prompt: VersionedPrompt,
    document_text: str,
) -> dict[str, Any]:
    """Llama a Claude con tool_choice forzado y devuelve el input del tool_use."""
    tool = _build_extraction_tool()
    user_message = prompt.user_template.format(document_text=document_text)
    tool_choice: ToolChoiceToolParam = {"type": "tool", "name": TOOL_NAME}
    messages: list[MessageParam] = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=prompt.system,
        tools=[tool],
        tool_choice=tool_choice,
        messages=messages,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            payload = block.input
            if not isinstance(payload, dict):
                msg = f"tool_use.input no es dict, es {type(payload).__name__}"
                raise ExtractionError(msg)
            return payload

    msg = (
        "El modelo no devolvió un bloque tool_use con el nombre esperado. "
        f"stop_reason={response.stop_reason}, content_types={[b.type for b in response.content]}"
    )
    raise ExtractionError(msg)


def extract_from_pdf(
    pdf_path: Path,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    client: anthropic.Anthropic | None = None,
    prompt: VersionedPrompt | None = None,
) -> ObstetricSummary:
    """Extrae un `ObstetricSummary` desde un PDF nativo de historia obstétrica.

    Args:
        pdf_path: Ruta al PDF.
        model: ID del modelo Claude. Default: env CLAUDE_MODEL o claude-sonnet-4-5-20250929.
        max_tokens: Máximo de tokens de salida. Default: env CLAUDE_MAX_TOKENS o 4096.
        client: Cliente Anthropic preconfigurado (útil para tests). Si None, se construye uno nuevo.
        prompt: Versión del prompt a usar. Si None, se usa la activa por default.

    Returns:
        ObstetricSummary validado.

    Raises:
        ExtractionError: si el PDF no se puede leer, si el modelo no responde
            como se espera, o si el output falla validación Pydantic.
    """
    resolved_model: str = model or os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL
    resolved_max_tokens = max_tokens or int(os.getenv("CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    resolved_prompt = prompt or get_active_prompt()

    document_text = _read_pdf_text(pdf_path)

    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            msg = "ANTHROPIC_API_KEY no está en el entorno. Crear .env desde .env.example."
            raise ExtractionError(msg)
        timeout = float(os.getenv("CLAUDE_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    raw_output = _call_model(
        client=client,
        model=resolved_model,
        max_tokens=resolved_max_tokens,
        prompt=resolved_prompt,
        document_text=document_text,
    )

    try:
        return ObstetricSummary.model_validate(raw_output)
    except ValidationError as exc:
        msg = f"El output del modelo no cumple el schema de ObstetricSummary: {exc}"
        raise ExtractionError(msg) from exc
