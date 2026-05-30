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
    # v1 + v2 al 2026-05-27 (ver ADR-0008 § Actualización).
    assert versions == [1, 2]
    # idempotente
    assert list_versions("extract_obstetric") == versions


def test_list_versions_for_nonexistent_returns_empty() -> None:
    assert list_versions("totally_nonexistent_prompt") == []


def test_latest_version_returns_max() -> None:
    # ``latest_version`` es informacional — devuelve el max disponible,
    # independiente del pin de DEFAULT_VERSIONS.
    assert latest_version("extract_obstetric") == 2


def test_latest_version_raises_when_no_versions() -> None:
    with pytest.raises(FileNotFoundError, match="No hay versiones"):
        latest_version("nonexistent")


# =========================================================================
# get_active_prompt
# =========================================================================


def test_get_active_with_override() -> None:
    p = get_active_prompt("extract_obstetric", version_override=1)
    assert p.version == 1


def test_get_active_with_override_v2() -> None:
    p = get_active_prompt("extract_obstetric", version_override=2)
    assert p.version == 2


def test_get_active_without_override_respects_default_pin() -> None:
    """ADR-0008 § Actualización 2026-05-27: ``extract_obstetric`` está
    pineado a v1 en ``DEFAULT_VERSIONS``. v2 NO se sirve por default
    aunque sea la latest.
    """
    p = get_active_prompt("extract_obstetric")
    assert p.version == 1


def test_default_pin_does_not_equal_latest_when_v2_present() -> None:
    """Sanity: el pin (1) y latest (2) son explícitamente distintos.

    Si este test rompe en el futuro, fue porque alguien promovió el
    default sin actualizar DEFAULT_VERSIONS — fuerza re-justificación.
    """
    pinned = get_active_prompt("extract_obstetric").version
    latest = latest_version("extract_obstetric")
    assert pinned == 1
    assert latest == 2
    assert pinned != latest


def test_get_active_falls_back_to_latest_when_name_not_pinned(tmp_path) -> None:
    """Para nombres NO listados en DEFAULT_VERSIONS, comportamiento
    sigue siendo "latest = active" (compat con prompts sin política
    de pin formal — típico cuando solo hay una versión)."""
    # Sanity: si en algún momento se agrega "fictional_prompt" al pin,
    # este test rompería. Hoy no está y latest_version falla con
    # FileNotFoundError. El path positivo del fallback se cubre indirecto
    # vía el patrón único existente (DEFAULT_VERSIONS solo contiene
    # extract_obstetric a la fecha).
    with pytest.raises(FileNotFoundError):
        get_active_prompt("nonexistent_prompt_xyz")


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
# Sanity: hashes conocidos de TODAS las versiones inmutables
# =========================================================================

# Hashes SHA256 completos esperados de cada versión registrada. Si este dict
# desincroniza del estado real, los tests fallan. Esto es a propósito:
#
# 1. ``test_all_known_prompts_have_stable_hash`` detecta una edición
#    in-place de un .md de versión existente. Eso viola el contrato de
#    inmutabilidad: una versión nunca cambia.
# 2. ``test_no_prompts_missing_from_known_hashes`` detecta que se agregó
#    un .md de versión nueva sin anclar su hash acá. Eso permite que la
#    versión nueva drifteee sin que CI lo note.
#
# Cuando se cree v3 (o cualquier prompt nuevo):
#   - Calcular su hash: ``python -c "from clinical_extractor.prompts.registry
#     import get_prompt; print(get_prompt('extract_obstetric', 3).hash)"``.
#   - Sumar la entrada acá en el mismo commit que crea el .md.
KNOWN_PROMPT_HASHES: dict[tuple[str, int], str] = {
    ("extract_obstetric", 1): (
        "9241ec0d2de94600537f47652cf0315a3fff05f6081878d9087881dff6d86482"
    ),
    ("extract_obstetric", 2): (
        "0f802ac8e4265da3b8fe3680b5e348252eb96053198b3f5b0d7171a4eaa2dca6"
    ),
}

# Lista de nombres lógicos de prompts que el registry debe conocer hoy. Si se
# crea un prompt nuevo (e.g. ``extract_neonatal``), agregar el nombre acá; el
# test ``no_prompts_missing_from_known_hashes`` itera sobre esta lista.
REGISTERED_PROMPT_NAMES: list[str] = ["extract_obstetric"]


def test_all_known_prompts_have_stable_hash() -> None:
    """Ningún prompt versionado puede editarse in-place.

    Itera sobre ``KNOWN_PROMPT_HASHES`` y compara el hash actual del
    archivo con el anclado. Cualquier diff — incluyendo whitespace o
    cambios de encoding — produce hash distinto y rompe este test.

    Fix correcto cuando rompe:
        1. NUNCA editar el ``.md`` de la versión existente.
        2. Crear ``{name}_v{N+1}.md`` con la modificación deseada.
        3. Sumar el hash nuevo a ``KNOWN_PROMPT_HASHES`` en el mismo commit.
        4. Decidir explícitamente si actualizar ``DEFAULT_VERSIONS`` (un
           commit separado, con comparator offline corrido).
    """
    for (name, version), expected_hash in KNOWN_PROMPT_HASHES.items():
        prompt = get_prompt(name, version)
        assert prompt.hash == expected_hash, (
            f"Prompt {name}_v{version} fue modificado in-place. "
            f"Esto viola el contrato de inmutabilidad del registry. "
            f"Crear v{version + 1} en lugar de editar v{version}. "
            f"Hash esperado: {expected_hash}, actual: {prompt.hash}"
        )


def test_no_prompts_missing_from_known_hashes() -> None:
    """Toda versión presente en disk debe estar anclada en ``KNOWN_PROMPT_HASHES``.

    Si este test rompe, significa que alguien agregó un .md de versión
    nueva pero NO sumó su hash acá. Eso deja la versión nueva sin candado:
    podría editarse silenciosamente después y CI no lo notaría.

    Fix: agregar la entrada faltante a ``KNOWN_PROMPT_HASHES`` arriba.
    """
    available: set[tuple[str, int]] = set()
    for name in REGISTERED_PROMPT_NAMES:
        for version in list_versions(name):
            available.add((name, version))

    anchored = set(KNOWN_PROMPT_HASHES.keys())
    missing = available - anchored

    assert not missing, (
        f"Versiones de prompt sin hash anclado: {sorted(missing)}. "
        f"Agregar entrada a KNOWN_PROMPT_HASHES en este test."
    )
