"""Prompts versionados del clinical-extractor — registry-backed.

Migración Fase 1 (ADR 0008): el contenido del prompt (system +
user_template) vive ahora en archivos ``.md`` bajo ``versions/``,
cargados por ``registry.py`` con hash determinístico. Este módulo
mantiene la API legacy (``VersionedPrompt``, ``PROMPT_REGISTRY``,
``get_active_prompt``, etc.) construyéndola sobre el registry, lo
que permite que el extractor existente siga funcionando sin cambios.

Reglas:
- NUNCA editar un prompt versionado in-place. Crear un nuevo file
  ``extract_obstetric_v{N+1}.md`` con el cambio.
- La versión activa se selecciona en ``get_active_prompt()``.
- Cambios de versión que afecten métricas requieren ADR y corrida
  completa de la suite de evals antes de merge.
- Para acceso a la API nueva (``PromptVersion``, ``list_versions``,
  ``latest_version``, etc.) importar desde
  ``clinical_extractor.prompts.registry``.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from clinical_extractor.prompts.registry import get_active_prompt as _registry_get_active

_logger = logging.getLogger(__name__)


class VersionedPrompt(NamedTuple):
    """Prompt con metadata de versión para audit trail.

    Forma legacy preservada (commit pre-registry): ``version``, ``system``
    y ``user_template`` son los 3 campos que el extractor consume vía
    ``request.prompt.user_template.format(document_text=...)``.

    La identidad del prompt para auditoría es ``version`` (string semver
    legacy) y, opcionalmente, el ``short_hash`` del registry. Para
    inspección del hash exacto, importar ``get_active_prompt`` del
    registry.
    """

    version: str
    system: str
    user_template: str


# Carga eager (al import) del prompt activo desde el registry.
# Cualquier error de parsing o file-not-found explota el import — es
# preferible falla al inicio que comportamiento degradado en runtime.
_active = _registry_get_active("extract_obstetric")

_logger.info(
    "Prompt activo: %s (hash=%s)",
    _active.version_string,
    _active.short_hash,
)


# Compat: la versión legacy se identificaba como "0.1.0" (semver). El
# registry usa enteros monotónicos. Conservamos la string legacy para
# que telemetry / logs / traces existentes no rompan formato — el hash
# del registry (en logs al import-time) es la nueva identidad canónica.
ACTIVE_PROMPT_VERSION = "0.1.0"

PROMPT_V0_1_0 = VersionedPrompt(
    version=ACTIVE_PROMPT_VERSION,
    system=_active.system,
    user_template=_active.user_template,
)

# Registry legacy — sigue siendo un dict de strings semver → VersionedPrompt.
# Cuando aparezca extract_obstetric_v2.md, agregar mapping manual aquí o
# refactor a uno cargado dinámicamente del registry.
PROMPT_REGISTRY: dict[str, VersionedPrompt] = {
    PROMPT_V0_1_0.version: PROMPT_V0_1_0,
}


def get_active_prompt() -> VersionedPrompt:
    """Devuelve la versión activa del prompt (legacy API, sin args)."""
    return PROMPT_REGISTRY[ACTIVE_PROMPT_VERSION]


def get_prompt(version: str) -> VersionedPrompt:
    """Devuelve una versión específica del prompt para evals retrospectivos.

    Argumento ``version`` es string semver ("0.1.0"), no entero del nuevo
    registry. Si necesitás cargar por entero, usar
    ``clinical_extractor.prompts.registry.get_prompt(name, version)``.
    """
    if version not in PROMPT_REGISTRY:
        msg = (
            f"Prompt version '{version}' no existe en el registry legacy. "
            f"Versiones disponibles: {list(PROMPT_REGISTRY.keys())}. "
            f"Para versiones nuevas (enteros), usar registry.get_prompt(name, int)."
        )
        raise KeyError(msg)
    return PROMPT_REGISTRY[version]
