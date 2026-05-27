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


def _build_key_in_text_pattern() -> re.Pattern[str]:
    """Construye regex que detecta ``{phi_key}{sep}{value}`` en texto plano.

    El propósito es cubrir mensajes de excepción y logs que serializan PHI
    como ``nombre=Maria`` o ``dni: 47812936`` — formato que la redacción
    por key de dict (en ``redact_phi``) NO detecta, y que los patterns
    inline (DNI / móvil / email) solo cubren parcialmente.

    Estrategia:

    - Alternancia con todas las keys de ``PHI_FIELDS_EXACT`` ordenadas por
      longitud descendente (matchear "nombre_paciente" antes de "nombre").
    - Case-insensitive **solo** para la key (``(?i:...)``). El resto del
      pattern es case-sensitive para que las heurísticas de uppercase
      (``[A-Z]{2,}``) sigan funcionando para detectar abreviaciones (DNI,
      HC) como sentinelas de fin de value.
    - Value: no-greedy, hasta 80 chars máx. Si el value es más largo que
      eso sin un delimitador interior, la regex completa falla y el value
      NO se redacta — limitación documentada en ADR-0009.
    - Lookahead que define dónde STOP capturar el value:
        1. Delimitador ``,;)}\n``
        2. Whitespace + palabra "normal" (lowercase 4+ chars con tildes)
        3. Whitespace + abreviación uppercase (``DNI``, ``HC``) seguida
           de whitespace / ``=`` / ``:`` / fin
        4. Whitespace + otra key PHI seguida de separador
        5. Fin de string
    """
    keys_alternation = "|".join(
        re.escape(k) for k in sorted(PHI_FIELDS_EXACT, key=len, reverse=True)
    )
    pattern = (
        # Boundary antes de la key (no word char inmediatamente antes).
        rf"(?<!\w)"
        # Key (case-insensitive solo en este grupo) capturada por nombre.
        rf"(?i:(?P<key>{keys_alternation}))"
        # Separator: = o : con whitespace opcional alrededor.
        rf"(?P<sep>\s*[=:]\s*)"
        # Value: comienza con no-whitespace, no-greedy, hasta 80 chars sin
        # ningún delimitador "duro" interno.
        rf"(?P<value>\S[^,;)}}\n]{{0,80}}?)"
        # Lookahead: define el fin del value (NO se consume).
        rf"(?="
        rf"\s*[,;)}}\n]"
        rf"|\s+[a-záéíóúñ]{{4,}}"
        rf"|\s+[A-ZÁÉÍÓÚÑ]{{2,}}(?=\s|[=:]|$)"
        rf"|\s+(?i:{keys_alternation})\s*[=:]"
        rf"|\s*$"
        rf")"
    )
    return re.compile(pattern)


# Compilado al import — costo de construcción se paga una sola vez por proceso.
_KEY_IN_TEXT_PATTERN = _build_key_in_text_pattern()


def _redact_phi_keys_in_text(text: str) -> str:
    """Redacta valores asociados a keys PHI cuando aparecen en texto plano.

    Ejemplos:

    - ``"nombre=Maria Lopez"`` → ``"nombre=[REDACTED]"``
    - ``"dni: 47812936"`` → ``"dni: [REDACTED]"``
    - ``"patient nombre=Maria dni=47812936"`` →
      ``"patient nombre=[REDACTED] dni=[REDACTED]"``

    Complementa ``redact_phi`` (keys de dict) y los patterns inline
    (DNI / teléfono / email) que cubren cada uno una superficie distinta.
    """

    def _replace(match: re.Match[str]) -> str:
        # Preserva la key original (case del input) y el separator con
        # whitespace original; solo reemplaza el value.
        return f"{match.group('key')}{match.group('sep')}{REDACTED_MARKER}"

    return _KEY_IN_TEXT_PATTERN.sub(_replace, text)

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
    """Aplica redaction a un string por contenido.

    Pipeline en dos capas (orden importa):

    1. **Patterns inline** — DNI peruano (8 dígitos), móvil peruano (9 dígitos
       prefijo 9), email. Se reemplazan donde aparezcan, sin necesidad de
       key contextual. Captura PHI "suelto" dentro de prosa.
    2. **Key-in-text** — secuencias ``{phi_key}{=|:}{value}`` donde la key
       pertenece a ``PHI_FIELDS_EXACT``. Captura PHI con identificador
       contextual (e.g. ``"nombre=Maria"``) que las patterns inline no ven.

    Orden: inline primero porque algunas excepciones traen DNI/email SIN
    una key adyacente (``"failed lookup of 47812936"``); ambas capas se
    aplican y el resultado es estable (idempotente).
    """
    value = DNI_PATTERN.sub(REDACTED_MARKER, value)
    value = PHONE_PATTERN.sub(REDACTED_MARKER, value)
    value = EMAIL_PATTERN.sub(REDACTED_MARKER, value)
    value = _redact_phi_keys_in_text(value)
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
