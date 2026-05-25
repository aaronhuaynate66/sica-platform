"""Runtime check de disponibilidad del paquete ``clinical_extractor``.

Aislado en su propio módulo para:

- **Caching**: el ``import`` real se ejecuta una sola vez por proceso
  (``functools.lru_cache``). Los handlers que pregunten por disponibilidad
  pagan el chequeo solo en el primer request post-startup.
- **Testabilidad**: tests que necesiten simular "módulo ausente" pueden
  ``monkeypatch`` esta función sin desinstalar el paquete.

Por qué no vive en ``Settings``:
``Settings`` refleja env vars y configuración estática. Que un paquete esté
o no instalado depende del entorno de ejecución, no de la configuración.
Mezclarlos llevaría a un Settings que cambia entre runs sin que la config
haya cambiado.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _cached_check() -> bool:
    try:
        import clinical_extractor  # noqa: F401
    except ImportError:
        return False
    return True


def extractor_module_available() -> bool:
    """True si ``clinical_extractor`` se puede importar en este proceso.

    Cached por ``functools.lru_cache``: el chequeo real (que toca
    ``importlib``) corre una vez. Tests que muten el resultado deben
    llamar a ``_cached_check.cache_clear()``.
    """
    return _cached_check()
