"""SICA API — backend FastAPI que expone el clinical-extractor.

Versión 0.1.0. Esta API es **interna**: no expone PHI a través de Internet
sin autenticación + autorización. En Fase 1 corre sólo en localhost del
partner o detrás de gateway autenticado.

Disclaimer regulatorio: el output de /extract es asistivo. Cada respuesta
debe ser revisada y confirmada por un médico antes de uso clínico. Ver
ADR 0003 y STRATEGY § 6.4.
"""

__version__ = "0.1.0"
