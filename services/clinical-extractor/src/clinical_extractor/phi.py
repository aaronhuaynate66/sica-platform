"""PHI redaction para cumplimiento Ley 29733 (Perú).

Aplica redaction recursiva a payloads antes de enviarlos a observability
externa (Langfuse Cloud). Los datos locales (logs, memoria, return del
extractor) NO se redactan — la sanitización se aplica solo en el punto
de inyección del SDK de Langfuse.

Ver ADR-0009 para la decisión y trade-offs.

API pública:

- ``redact_phi(payload)`` — recursiva, pura, idempotente. Devuelve una
  nueva estructura sin mutar el input.
- ``redact_filename(filename)`` — reemplaza filenames que pueden
  contener nombre de paciente, preservando prefijos sintéticos
  conocidos.
- ``PHI_FIELDS_EXACT`` — lista canónica de keys consideradas PHI.
  Sincronizar manualmente con ``ObstetricSummary`` cuando el schema
  evolucione.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("clinical_extractor.phi")


# Lista canónica de campos PHI. Match case-insensitive sobre la key.
# Sincronizar manualmente con ObstetricSummary schema cuando se agreguen
# campos nuevos que identifiquen al paciente.
PHI_FIELDS_EXACT: frozenset[str] = frozenset(
    {
        # Identidad personal
        "nombre",
        "nombres",
        "apellidos",
        "nombre_completo",
        "nombre_paciente",
        "paciente_nombre",
        "patient_name",
        "first_name",
        "last_name",
        "full_name",
        # Documentos
        "dni",
        "cedula",
        "documento",
        "documento_identidad",
        "identification",
        "id_document",
        # HC
        "numero_hc",
        "hc_id",
        "hc_numero",
        "historia_clinica",
        "medical_record_number",
        "mrn",
        # Contacto
        "direccion",
        "address",
        "telefono",
        "phone",
        "email",
        "contacto",
        # Médico tratante
        "medico_tratante",
        "nombre_medico",
        "cmp",
        "doctor_name",
        "physician_name",
        "attending_physician",
        # Establecimiento (cuando identificable)
        "establecimiento",
        "establecimiento_salud",
        "clinica",
        "hospital",
        "facility_name",
        # Fechas con DOB exacto (riesgo de reidentificación)
        "fecha_nacimiento",
        "fecha_de_nacimiento",
        "date_of_birth",
        "dob",
        "birthdate",
        "birth_date",
    }
)

# Patrones de PHI por contenido. Heurística para PHI inline en campos
# no listados arriba (e.g. notes_summary que copia un DNI desde el PDF).
DNI_PATTERN = re.compile(r"\b\d{8}\b")  # DNI peruano: 8 dígitos.
PHONE_PATTERN = re.compile(r"\b9\d{8}\b")  # móvil peruano: 9 dígitos, prefijo 9.
EMAIL_PATTERN = re.compile(r"\b[\w.-]+@[\w.-]+\.\w+\b")

REDACTED_MARKER = "[REDACTED]"

# Prefijos de filename que NO contienen PHI (sintéticos, fixtures, longitudinales
# del paciente didáctico "lucia"). Se preservan tal cual.
_SAFE_FILENAME_PREFIXES: tuple[str, ...] = (
    "synthetic_",
    "longitudinal_lucia_",
    "test_",
    "fixture_",
)


def _is_phi_field(key: str) -> bool:
    """Determina si una key corresponde a campo PHI canónico (case-insensitive)."""
    return key.lower() in PHI_FIELDS_EXACT


def _redact_string_content(value: str) -> str:
    """Aplica redaction a un string por contenido (patrones).

    DNI / teléfono / email se reemplazan inline por ``[REDACTED]``,
    preservando el resto del string. Idempotente: aplicar dos veces
    da el mismo resultado.
    """
    value = DNI_PATTERN.sub(REDACTED_MARKER, value)
    value = PHONE_PATTERN.sub(REDACTED_MARKER, value)
    value = EMAIL_PATTERN.sub(REDACTED_MARKER, value)
    return value


def redact_phi(payload: Any) -> Any:
    """Redacción recursiva de PHI en cualquier estructura JSON-serializable.

    Reglas:

    - ``dict``: revisa keys; si la key es PHI canónico (case-insensitive),
      el value entero se reemplaza por ``[REDACTED]`` (o ``["[REDACTED]"]``
      si era una lista no vacía). En caso contrario, recurre sobre el value.
    - ``list``: recurre sobre cada elemento.
    - ``str``: aplica patrones de contenido (DNI / teléfono / email inline).
    - ``int`` / ``float`` / ``bool`` / ``None``: passthrough.

    Propiedades:

    - **Pura**: no muta el input. Devuelve siempre una nueva estructura.
    - **Idempotente**: ``redact_phi(redact_phi(x)) == redact_phi(x)``.
    - **Total**: cualquier estructura JSON-serializable se procesa sin
      excepción (objetos custom pasan por la rama final tal cual).
    """
    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if _is_phi_field(key):
                # Key es PHI canónico → reemplazar el value entero.
                if isinstance(value, list):
                    result[key] = [REDACTED_MARKER] if value else []
                else:
                    result[key] = REDACTED_MARKER
            else:
                result[key] = redact_phi(value)
        return result
    if isinstance(payload, list):
        return [redact_phi(item) for item in payload]
    if isinstance(payload, str):
        return _redact_string_content(payload)
    # int, float, bool, None — passthrough.
    return payload


def redact_filename(filename: str) -> str:
    """Sanitiza nombres de archivo que pueden contener PHI.

    Estrategia conservadora:

    - Filenames con prefijos seguros conocidos (``synthetic_``,
      ``longitudinal_lucia_``, ``test_``, ``fixture_``) se preservan
      tal cual — no contienen PHI por construcción.
    - Cualquier otro filename se reemplaza por ``[REDACTED]{extension}``,
      preservando solo el sufijo (``.pdf``, ``.json``) para mantener
      pistas de formato en el dashboard.

    Si el filename está vacío o no se puede parsear, devuelve el marker
    sin extensión.
    """
    if not filename:
        return REDACTED_MARKER
    try:
        name = Path(filename).stem
        suffix = Path(filename).suffix
    except Exception:
        return REDACTED_MARKER
    if name.startswith(_SAFE_FILENAME_PREFIXES):
        return filename
    return f"{REDACTED_MARKER}{suffix}"


__all__ = [
    "PHI_FIELDS_EXACT",
    "REDACTED_MARKER",
    "redact_filename",
    "redact_phi",
]
