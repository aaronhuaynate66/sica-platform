"""Tests del registry de prompts (Fase 1, ADR 0008).

Cobertura:
- Carga de un prompt existente devuelve PromptVersion completo.
- Carga de nombre/versión inexistente levanta FileNotFoundError.
- Hash es determinístico para mismo contenido y distinto para diff content.
- Parser extrae SYSTEM + USER_TEMPLATE separados correctamente.
- list_versions / latest_version / get_active_prompt funcionan según contrato.
- Cache (lru_cache) devuelve mismo objeto; clear_cache invalida.
- _parse_filename maneja formatos inválidos.
- Compat legacy: ``VersionedPrompt``, ``PROMPT_V0_1_0`` y
  ``get_active_prompt()`` legacy siguen funcionando + el contenido
  coincide con el del registry.
"""

from __future__ import annotations

import pytest

from clinical_extractor.prompts import (
    ACTIVE_PROMPT_VERSION,
    PROMPT_REGISTRY,
    PROMPT_V0_1_0,
    VersionedPrompt,
)
from clinical_extractor.prompts import get_active_prompt as legacy_get_active_prompt
from clinical_extractor.prompts.registry import (
    PromptVersion,
    _compute_hash,
    _parse_filename,
    _parse_markdown_sections,
    clear_cache,
    get_active_prompt,
    get_prompt,
    latest_version,
    list_versions,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_cache()
    yield
    clear_cache()


# =========================================================================
# get_prompt / load
# =========================================================================


def test_load_existing_prompt_returns_version() -> None:
    p = get_prompt("extract_obstetric", 1)
    assert p is not None
    assert isinstance(p, PromptVersion)
    assert p.name == "extract_obstetric"
    assert p.version == 1
    assert len(p.system) > 0
    assert len(p.user_template) > 0
    assert len(p.hash) == 64  # SHA256 hex
    assert p.raw_content.startswith("# extract_obstetric_v1") or "## SYSTEM" in p.raw_content


def test_load_nonexistent_prompt_raises() -> None:
    with pytest.raises(FileNotFoundError, match="no encontrado"):
        get_prompt("nonexistent_prompt_xyz", 1)


def test_load_nonexistent_version_raises() -> None:
    with pytest.raises(FileNotFoundError):
        get_prompt("extract_obstetric", 999)


# =========================================================================
# Hash invariants
# =========================================================================


def test_hash_is_deterministic() -> None:
    p1 = get_prompt("extract_obstetric", 1)
    clear_cache()
    p2 = get_prompt("extract_obstetric", 1)
    assert p1.hash == p2.hash


def test_hash_changes_with_content(tmp_path) -> None:
    """Dos strings distintos deben producir hashes distintos."""
    h1 = _compute_hash("contenido uno")
    h2 = _compute_hash("contenido dos")
    assert h1 != h2
    # mismo contenido produce mismo hash
    assert _compute_hash("contenido uno") == h1


def test_short_hash_is_8_chars() -> None:
    p = get_prompt("extract_obstetric", 1)
    assert len(p.short_hash) == 8
    assert p.short_hash == p.hash[:8]


def test_version_string_format() -> None:
    p = get_prompt("extract_obstetric", 1)
    assert p.version_string == "extract_obstetric_v1"


# =========================================================================
# Markdown parser
# =========================================================================


def test_parse_markdown_sections_extracts_both() -> None:
    raw = "# header\n\n## SYSTEM\nMy system text\n\n## USER_TEMPLATE\nMy user text {document_text}\n"
    sys_text, usr_text = _parse_markdown_sections(raw)
    assert sys_text == "My system text"
    assert usr_text == "My user text {document_text}"


def test_parse_markdown_sections_missing_system_raises() -> None:
    raw = "## USER_TEMPLATE\nMy user text"
    with pytest.raises(ValueError, match="SYSTEM"):
        _parse_markdown_sections(raw)


def test_parse_markdown_sections_missing_user_raises() -> None:
    raw = "## SYSTEM\nMy system"
    with pytest.raises(ValueError, match="USER_TEMPLATE"):
        _parse_markdown_sections(raw)


def test_parse_markdown_sections_wrong_order_raises() -> None:
    raw = "## USER_TEMPLATE\nu\n## SYSTEM\ns"
    with pytest.raises(ValueError, match="antes"):
        _parse_markdown_sections(raw)


# =========================================================================
# Versions listing
# =========================================================================


def test_list_versions_returns_sorted() -> None:
    versions = list_versions("extract_obstetric")
    assert versions == [1]
    # idempotente
    assert list_versions("extract_obstetric") == versions


def test_list_versions_for_nonexistent_returns_empty() -> None:
    assert list_versions("totally_nonexistent_prompt") == []


def test_latest_version_returns_max() -> None:
    assert latest_version("extract_obstetric") == 1


def test_latest_version_raises_when_no_versions() -> None:
    with pytest.raises(FileNotFoundError, match="No hay versiones"):
        latest_version("nonexistent")


# =========================================================================
# get_active_prompt
# =========================================================================


def test_get_active_with_override() -> None:
    p = get_active_prompt("extract_obstetric", version_override=1)
    assert p.version == 1


def test_get_active_without_override_uses_latest() -> None:
    p = get_active_prompt("extract_obstetric")
    assert p.version == latest_version("extract_obstetric")


# =========================================================================
# Cache behavior
# =========================================================================


def test_cache_works() -> None:
    p1 = get_prompt("extract_obstetric", 1)
    p2 = get_prompt("extract_obstetric", 1)
    assert p1 is p2  # exact object identity gracias a lru_cache


def test_clear_cache_resets() -> None:
    p1 = get_prompt("extract_obstetric", 1)
    clear_cache()
    p2 = get_prompt("extract_obstetric", 1)
    assert p1 is not p2  # objeto distinto post-clear
    # pero el contenido es idéntico
    assert p1.hash == p2.hash
    assert p1.system == p2.system


# =========================================================================
# Filename parser
# =========================================================================


def test_parse_filename_valid() -> None:
    assert _parse_filename("extract_obstetric_v1.md") == ("extract_obstetric", 1)
    assert _parse_filename("foo_v42.md") == ("foo", 42)


def test_parse_filename_invalid_returns_none() -> None:
    # No tiene _v
    assert _parse_filename("no_version_format.md") is None
    # Termina con _v pero sin número
    assert _parse_filename("missing_v.md") is None
    # _v sin número después
    assert _parse_filename("extract_v.md") is None
    # No es .md
    assert _parse_filename("extract_obstetric_v1.txt") is None
    # _v con letras
    assert _parse_filename("foo_vABC.md") is None


# =========================================================================
# Compat legacy API
# =========================================================================


def test_legacy_active_prompt_version_is_semver_string() -> None:
    assert ACTIVE_PROMPT_VERSION == "0.1.0"


def test_legacy_get_active_prompt_returns_named_tuple() -> None:
    p = legacy_get_active_prompt()
    assert isinstance(p, VersionedPrompt)
    assert p.version == "0.1.0"
    assert "asistente clínico" in p.system
    assert "{document_text}" in p.user_template


def test_legacy_prompt_registry_dict_has_v0_1_0() -> None:
    assert "0.1.0" in PROMPT_REGISTRY
    assert PROMPT_REGISTRY["0.1.0"] is PROMPT_V0_1_0


def test_legacy_content_matches_registry() -> None:
    """Garantía Fase 1: el VersionedPrompt legacy y el PromptVersion del
    registry exponen el mismo system + user_template."""
    legacy = legacy_get_active_prompt()
    new = get_active_prompt("extract_obstetric")
    assert legacy.system == new.system
    assert legacy.user_template == new.user_template


# =========================================================================
# Sanity hash conocido
# =========================================================================


def test_known_prompt_hash_is_stable() -> None:
    """Documenta el hash exacto del prompt v1 al momento del commit.

    Si este test rompe en el futuro, significa que alguien modificó
    extract_obstetric_v1.md (ya sea contenido, whitespace o encoding).
    Eso viola la regla "una versión nunca cambia in-place". El fix
    correcto es crear extract_obstetric_v2.md y dejar v1 intacta.
    """
    p = get_prompt("extract_obstetric", 1)
    # Hash conocido al momento del commit del Bloque 1.
    expected_hash_prefix = "9241ec0d"
    assert p.short_hash == expected_hash_prefix, (
        f"Hash del prompt v1 cambió. Si fue intencional, crear v2 y "
        f"NO modificar v1 in-place. Hash actual: {p.short_hash}"
    )
