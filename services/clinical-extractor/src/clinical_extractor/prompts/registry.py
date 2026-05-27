"""Prompt registry con versionado, hashing determinístico y carga dinámica.

Diseño Fase 1 (ADR 0008):

- Cada versión de un prompt vive en un archivo ``.md`` independiente:
  ``versions/{nombre_logico}_v{N}.md``.
- El contenido se separa en dos secciones por marcadores
  ``## SYSTEM`` y ``## USER_TEMPLATE``. Decisión: un solo file por
  versión preserva atomicidad y diffs limpios; los dos prompts
  (system + user_template) son inseparables semánticamente.
- ``PromptVersion`` expone ``system``, ``user_template``, y un
  ``hash`` SHA256 del raw content completo del archivo (incluyendo
  marcadores y header). Cualquier cambio — incluso whitespace —
  produce un hash distinto. Esto previene drift silencioso.
- Carga cached con ``lru_cache``: el archivo se lee una vez por
  proceso. ``clear_cache()`` para tests.
- ``get_active_prompt(name, version_override=None)``: por default
  usa la versión más alta disponible. Fase 2 agregará routing A/B
  acá. Fase 3 agregará rollback automático en regresión.

La API legacy de ``clinical_extractor.prompts`` (``VersionedPrompt``,
``PROMPT_REGISTRY``, ``ACTIVE_PROMPT_VERSION``, ``get_active_prompt``
sin args, ``get_prompt(version: str)``) sigue funcionando — está
implementada como wrapper sobre este registry en ``__init__.py``.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

logger = logging.getLogger("clinical_extractor.prompts.registry")

PROMPTS_DIR = Path(__file__).parent / "versions"

# Marcadores que separan SYSTEM y USER_TEMPLATE dentro del .md file.
# Cualquier cambio en estos marcadores rompe el parser — son contrato.
_SYSTEM_MARKER = "## SYSTEM"
_USER_MARKER = "## USER_TEMPLATE"

# Versión "default" explícita por nombre lógico. Cuando un nombre aparece
# acá, ``get_active_prompt`` SIN override usa este pin en vez de
# ``latest_version``. Diseño (ADR-0008 § Actualización 2026-05-27):
#
# - El comportamiento ingenuo "latest = default" promueve cualquier
#   versión nueva en cuanto se commitea su .md, sin validación. Para
#   prompts clínicos eso es peligroso — un v_new no probado puede
#   regresionar métricas críticas.
# - El pin desacopla "qué versiones existen" (registry inmutable) de
#   "cuál se sirve por default" (decisión operativa). Bumpear el
#   default es un commit explícito separado del commit que introduce
#   la nueva versión — permite ventana de validación.
# - Nombres NO listados acá caen al fallback ``latest_version`` (compat
#   con el comportamiento original cuando solo hay una versión).
DEFAULT_VERSIONS: dict[str, int] = {
    # extract_obstetric: pinned a v1 mientras v2 está en validación. La
    # promoción a v2 requiere comparator offline + revisión clínica.
    "extract_obstetric": 1,
}


@dataclass(frozen=True)
class PromptVersion:
    """Una versión específica de un prompt.

    Atributos:
        name: Identificador lógico estable (e.g. ``extract_obstetric``).
        version: Entero monotónicamente creciente.
        system: Texto del system prompt (sin marcadores).
        user_template: Texto del user template (sin marcadores) — debe
            contener ``{document_text}`` como placeholder.
        hash: SHA256 hex del raw content del archivo completo.
        raw_content: Contenido bruto del file (header + marcadores +
            ambos prompts). Conservado para auditoría / diff.
        file_path: Path absoluto al ``.md``.
    """

    name: str
    version: int
    system: str
    user_template: str
    hash: str
    raw_content: str
    file_path: Path

    @property
    def version_string(self) -> str:
        """Identificador legible: ``extract_obstetric_v1``."""
        return f"{self.name}_v{self.version}"

    @property
    def short_hash(self) -> str:
        """Primeros 8 chars del hash, para logs."""
        return self.hash[:8]


def _compute_hash(content: str) -> str:
    """SHA256 hex determinístico del contenido en UTF-8."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse_filename(filename: str) -> tuple[str, int] | None:
    """Parsea ``extract_obstetric_v1.md`` → ``("extract_obstetric", 1)``.

    Retorna ``None`` si no matchea el formato esperado
    (``{name}_v{int}.md``).
    """
    if not filename.endswith(".md"):
        return None
    stem = filename[:-3]
    # `rsplit("_v", 1)` es el split correcto: el nombre puede contener
    # underscores y "v" embebidos (e.g. "extract_v0_obstetric_v1.md"
    # → ("extract_v0_obstetric", 1)).
    parts = stem.rsplit("_v", 1)
    if len(parts) != 2:
        return None
    name, version_str = parts
    if not version_str.isdigit() or not name:
        return None
    return name, int(version_str)


def _parse_markdown_sections(raw_content: str) -> tuple[str, str]:
    """Extrae las secciones SYSTEM y USER_TEMPLATE del raw content.

    Returns:
        Tupla ``(system, user_template)`` — strings con whitespace
        trailing stripped pero sin alteración interna.

    Raises:
        ValueError: si los marcadores no aparecen o aparecen en orden
        incorrecto. El archivo debe tener primero ``## SYSTEM`` y luego
        ``## USER_TEMPLATE``.
    """
    sys_match = re.search(rf"^{re.escape(_SYSTEM_MARKER)}\s*$", raw_content, re.MULTILINE)
    user_match = re.search(rf"^{re.escape(_USER_MARKER)}\s*$", raw_content, re.MULTILINE)
    if sys_match is None:
        msg = f"Marcador '{_SYSTEM_MARKER}' no encontrado en el prompt file"
        raise ValueError(msg)
    if user_match is None:
        msg = f"Marcador '{_USER_MARKER}' no encontrado en el prompt file"
        raise ValueError(msg)
    if sys_match.start() >= user_match.start():
        msg = f"'{_SYSTEM_MARKER}' debe aparecer antes de '{_USER_MARKER}'"
        raise ValueError(msg)

    system_block = raw_content[sys_match.end() : user_match.start()]
    user_block = raw_content[user_match.end() :]
    # Strip de newline justo después del marcador + whitespace trailing.
    system_text = system_block.strip("\n").rstrip()
    user_text = user_block.strip("\n").rstrip()
    return system_text, user_text


@cache
def _load_prompt(name: str, version: int) -> PromptVersion:
    """Carga un prompt específico desde disk. Cached por (name, version)."""
    file_path = PROMPTS_DIR / f"{name}_v{version}.md"
    if not file_path.exists():
        msg = f"Prompt no encontrado: {name}_v{version} en {PROMPTS_DIR}"
        raise FileNotFoundError(msg)
    raw = file_path.read_text(encoding="utf-8")
    system, user_template = _parse_markdown_sections(raw)
    return PromptVersion(
        name=name,
        version=version,
        system=system,
        user_template=user_template,
        hash=_compute_hash(raw),
        raw_content=raw,
        file_path=file_path,
    )


def get_prompt(name: str, version: int) -> PromptVersion:
    """API pública para obtener un prompt por nombre + versión."""
    return _load_prompt(name, version)


def list_versions(name: str) -> list[int]:
    """Lista todas las versiones disponibles para un nombre lógico."""
    if not PROMPTS_DIR.exists():
        return []
    versions: list[int] = []
    for file in PROMPTS_DIR.iterdir():
        parsed = _parse_filename(file.name)
        if parsed is not None and parsed[0] == name:
            versions.append(parsed[1])
    return sorted(versions)


def latest_version(name: str) -> int:
    """Número de versión más alto disponible para un prompt."""
    versions = list_versions(name)
    if not versions:
        msg = f"No hay versiones disponibles de prompt '{name}'"
        raise FileNotFoundError(msg)
    return max(versions)


def get_active_prompt(
    name: str, version_override: int | None = None
) -> PromptVersion:
    """Versión "activa" de un prompt.

    Lógica:

    - ``version_override`` provisto → carga esa versión exacta (siempre
      gana sobre el default y sobre latest).
    - ``name`` listado en ``DEFAULT_VERSIONS`` → usa ese pin.
    - Si no, fallback a ``latest_version(name)`` (compat con prompts que
      no requieren validación previa por tener una sola versión).

    Fase 2 agregará rutas A/B aquí (split por hash de request, etc.).
    """
    if version_override is not None:
        return get_prompt(name, version_override)
    pinned = DEFAULT_VERSIONS.get(name)
    if pinned is not None:
        return get_prompt(name, pinned)
    return get_prompt(name, latest_version(name))


def clear_cache() -> None:
    """Limpia el cache de prompts. Útil en tests que mutan archivos."""
    _load_prompt.cache_clear()
