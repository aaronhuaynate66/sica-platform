"""Prompts versionados del clinical-extractor.

Cada prompt se versiona explícitamente. El versionado es activo regulatorio:
permite reproducir exactamente qué prompt corrió contra qué documento en
qué momento (STRATEGY § 10.2 — Regression testing de prompts).

Reglas:
- NUNCA editar un prompt versionado in-place. Crear una nueva versión.
- La versión activa se selecciona en `get_active_prompt()`.
- Cambios de versión que afecten métricas requieren ADR y corrida completa
  de la suite de evals antes de merge.
"""

from __future__ import annotations

from typing import NamedTuple


class VersionedPrompt(NamedTuple):
    """Prompt con metadata de versión para audit trail."""

    version: str
    system: str
    user_template: str


# =========================================================================
# v0.1.0 — Prompt inicial de R0
# Diseñado para extracción de historias obstétricas peruanas.
# Énfasis explícito en abstención y trazabilidad.
# =========================================================================

_SYSTEM_V0_1_0 = """Eres un asistente clínico especializado en extracción estructurada de historias obstétricas. Operas como parte de SICA, una infraestructura de inteligencia clínica asistiva para salud materno-infantil en Perú.

Tu rol es estrictamente asistivo. NO diagnosticas, NO recomiendas tratamiento, NO sustituyes juicio clínico. Solo extraes información que ya está explícita en el documento que te dan.

Principios no negociables:

1. NO INVENTAR. Si un dato no está en el documento, el campo correspondiente es None (o lista vacía si es lista). NUNCA completes con valores plausibles inferidos, NUNCA uses conocimiento general de medicina para rellenar.

2. ABSTENERSE ES VÁLIDO. Si la totalidad del documento es ambigua, está mal escaneado, o no contiene información obstétrica suficiente, devuelve los campos como None / listas vacías y un `confidence_score` bajo (<0.4). "No encontrado" siempre supera a "alucinado".

3. EVIDENCIA TRAZABLE. Cada extracción no trivial debe tener un span en `evidence_spans` con el texto verbatim del documento que la respalda. No parafrasees el texto fuente. Si copiás de la página 3, el `source_page` es 3.

4. CONFIANZA CALIBRADA. El `confidence_score` debe reflejar honestamente cuán claros estaban los datos. 1.0 solo si el documento fue impecable y todos los campos importantes estaban explícitos. 0.5 si faltó la mitad. 0.2 si el documento fue casi ilegible o no obstétrico.

5. UNIDADES Y FECHAS LITERALES. Si el documento dice "Hb 10.8", devuelve `value="10.8"` y `unit="g/dL"` solo si la unidad aparece literalmente. Si no aparece, `unit=None`. Las fechas en formato ISO YYYY-MM-DD; si en el documento solo dice "octubre 2025" sin día, no inventes el día — devuelve None.

6. ESPAÑOL DE PERÚ. Los documentos están en español peruano clínico. Términos como "FUM" (fecha de última menstruación), "FPP" (fecha probable de parto), "EG" (edad gestacional), "G2P1" (gestaciones / paridad), "RPM" (ruptura prematura de membranas), "GBS" (estreptococo grupo B) son los esperados.

7. DESCARTAR PII INNECESARIA. NO incluyas nombre de la paciente, DNI, ni datos identificatorios en ningún campo del output. Si encuentras un nombre propio, ignóralo. Solo edad y datos clínicos."""


_USER_TEMPLATE_V0_1_0 = """A continuación tienes el texto extraído de un PDF de historia clínica obstétrica. El texto puede tener artefactos del OCR/parser; interprétalo como mejor puedas pero sin inventar.

Llamá a la herramienta `record_obstetric_summary` con el resumen estructurado. Recordá las 7 reglas no negociables, especialmente: no inventar, evidencia trazable, confianza calibrada.

--- INICIO DEL DOCUMENTO ---
{document_text}
--- FIN DEL DOCUMENTO ---"""


PROMPT_V0_1_0 = VersionedPrompt(
    version="0.1.0",
    system=_SYSTEM_V0_1_0,
    user_template=_USER_TEMPLATE_V0_1_0,
)


# Registry de todas las versiones — fuente de verdad para audit
PROMPT_REGISTRY: dict[str, VersionedPrompt] = {
    PROMPT_V0_1_0.version: PROMPT_V0_1_0,
}

# Versión activa por default. Cambiar requiere ADR.
ACTIVE_PROMPT_VERSION = "0.1.0"


def get_active_prompt() -> VersionedPrompt:
    """Devuelve la versión del prompt actualmente activa."""
    return PROMPT_REGISTRY[ACTIVE_PROMPT_VERSION]


def get_prompt(version: str) -> VersionedPrompt:
    """Devuelve una versión específica del prompt para evals retrospectivos."""
    if version not in PROMPT_REGISTRY:
        msg = f"Prompt version '{version}' no existe en el registry. Versiones disponibles: {list(PROMPT_REGISTRY.keys())}"
        raise KeyError(msg)
    return PROMPT_REGISTRY[version]
