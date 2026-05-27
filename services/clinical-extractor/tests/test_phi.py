"""Tests del módulo ``clinical_extractor.phi``.

Cubren las propiedades clave del redactor (ADR-0009):

- Recursión sobre dicts y listas anidadas.
- Match case-insensitive de keys PHI.
- Patrones inline (DNI 8-dig, móvil 9-dig, email).
- Idempotencia: aplicar dos veces da el mismo resultado.
- Pureza: el input no se muta.
- Preservación de datos clínicos no-PHI.
- Filename sanitization con prefijos seguros.
- Passthrough de primitivos.
"""

from __future__ import annotations

from clinical_extractor.phi import (
    PHI_FIELDS_EXACT,
    REDACTED_MARKER,
    redact_filename,
    redact_phi,
)

# =========================================================================
# redact_phi — contenido inline (DNI, teléfono, email)
# =========================================================================


def test_redact_phi_string_dni_inline() -> None:
    """DNI peruano (8 dígitos) inline se redacta preservando el resto."""
    assert redact_phi("Paciente DNI 47812936 acude") == f"Paciente DNI {REDACTED_MARKER} acude"


def test_redact_phi_string_phone() -> None:
    """Teléfono móvil peruano (9 dígitos prefijo 9) inline se redacta."""
    assert redact_phi("Tel: 987654321") == f"Tel: {REDACTED_MARKER}"


def test_redact_phi_string_email() -> None:
    """Email inline se redacta."""
    assert redact_phi("Email lucia@gmail.com") == f"Email {REDACTED_MARKER}"


def test_redact_phi_multiple_inline_patterns_in_same_string() -> None:
    """Múltiples patrones en el mismo string: todos se redactan."""
    text = "Paciente 47812936 tel 987654321 email lucia@gmail.com"
    result = redact_phi(text)
    assert "47812936" not in result
    assert "987654321" not in result
    assert "lucia@gmail.com" not in result
    assert result.count(REDACTED_MARKER) == 3


# =========================================================================
# redact_phi — keys PHI canónicas
# =========================================================================


def test_redact_phi_dict_with_phi_key() -> None:
    """Key PHI canónica → value reemplazado entero por REDACTED."""
    result = redact_phi({"nombre": "Lucia", "edad": 28})
    assert result == {"nombre": REDACTED_MARKER, "edad": 28}


def test_redact_phi_nested_dict() -> None:
    """Recursión sobre dicts anidados — todas las keys PHI se redactan."""
    payload = {"paciente": {"dni": "47812936", "nombre": "Lucia Mendoza"}}
    expected = {"paciente": {"dni": REDACTED_MARKER, "nombre": REDACTED_MARKER}}
    assert redact_phi(payload) == expected


def test_redact_phi_list_of_strings_inline_patterns() -> None:
    """Listas de strings: cada string pasa por el redactor de contenido."""
    result = redact_phi(["Maria 12345678 control prenatal"])
    assert result == [f"Maria {REDACTED_MARKER} control prenatal"]


def test_redact_phi_case_insensitive_keys() -> None:
    """Match de PHI_FIELDS_EXACT es case-insensitive."""
    result = redact_phi({"NOMBRE": "Lucia", "Nombre": "M", "DNI": "47812936"})
    assert result["NOMBRE"] == REDACTED_MARKER
    assert result["Nombre"] == REDACTED_MARKER
    assert result["DNI"] == REDACTED_MARKER


# =========================================================================
# Datos clínicos no-PHI se preservan
# =========================================================================


def test_redact_phi_preserves_clinical_data() -> None:
    """Campos clínicos legítimos (edad, problemas, semanas) pasan sin cambio."""
    payload = {
        "gestational_age_weeks": 24.3,
        "active_problems": ["Diabetes gestacional", "Anemia leve"],
        "confidence_score": 0.92,
        "patient_age": 28,
    }
    result = redact_phi(payload)
    assert result == payload  # idéntico


# =========================================================================
# Idempotencia + pureza
# =========================================================================


def test_redact_phi_idempotent() -> None:
    """``redact_phi(redact_phi(x)) == redact_phi(x)`` para cualquier x."""
    payload = {
        "nombre": "Lucia",
        "dni": "47812936",
        "notes_summary": "Paciente DNI 47812936 con email test@x.com",
        "active_problems": ["Anemia"],
    }
    once = redact_phi(payload)
    twice = redact_phi(once)
    assert once == twice


def test_redact_phi_pure_no_mutation() -> None:
    """El input no debe ser mutado en ninguna profundidad."""
    payload = {"nombre": "Lucia", "paciente": {"dni": "47812936"}}
    snapshot = {"nombre": "Lucia", "paciente": {"dni": "47812936"}}
    _ = redact_phi(payload)
    assert payload == snapshot


# =========================================================================
# Primitivos y estructuras vacías
# =========================================================================


def test_redact_phi_passthrough_primitives() -> None:
    """int / float / bool / None pasan sin tocar."""
    assert redact_phi(42) == 42
    assert redact_phi(3.14) == 3.14
    assert redact_phi(None) is None
    assert redact_phi(True) is True
    assert redact_phi(False) is False


def test_redact_phi_empty_structures() -> None:
    """Estructuras vacías se devuelven vacías."""
    assert redact_phi({}) == {}
    assert redact_phi([]) == []
    assert redact_phi("") == ""


def test_redact_phi_phi_key_with_empty_list() -> None:
    """Key PHI con lista vacía → lista vacía (no [REDACTED])."""
    assert redact_phi({"nombres": []}) == {"nombres": []}


def test_redact_phi_phi_key_with_nonempty_list() -> None:
    """Key PHI con lista no vacía → lista con un solo [REDACTED]."""
    assert redact_phi({"nombres": ["Lucia", "Maria"]}) == {"nombres": [REDACTED_MARKER]}


# =========================================================================
# redact_filename
# =========================================================================


def test_redact_filename_preserves_synthetic() -> None:
    """Prefijo ``synthetic_`` indica caso sintético — se preserva."""
    assert redact_filename("synthetic_case_01.pdf") == "synthetic_case_01.pdf"


def test_redact_filename_preserves_longitudinal_lucia() -> None:
    """Prefijo ``longitudinal_lucia_`` es el paciente didáctico — preservado."""
    assert redact_filename("longitudinal_lucia_sem16.pdf") == "longitudinal_lucia_sem16.pdf"


def test_redact_filename_preserves_test_and_fixture() -> None:
    """Prefijos de test/fixture preservados (no llevan PHI por construcción)."""
    assert redact_filename("test_caso_borde.pdf") == "test_caso_borde.pdf"
    assert redact_filename("fixture_pdf_escaneado.pdf") == "fixture_pdf_escaneado.pdf"


def test_redact_filename_redacts_phi_bearing_filename() -> None:
    """Filename sin prefijo seguro se reemplaza por [REDACTED].{suffix}."""
    assert redact_filename("maria_lopez_hc2024.pdf") == f"{REDACTED_MARKER}.pdf"


def test_redact_filename_preserves_extension_for_redacted() -> None:
    """La extensión se preserva incluso al redactar."""
    assert redact_filename("paciente.json") == f"{REDACTED_MARKER}.json"


def test_redact_filename_empty_string() -> None:
    """Filename vacío → marker sin extensión."""
    assert redact_filename("") == REDACTED_MARKER


# =========================================================================
# Schema-level sanity: PHI_FIELDS_EXACT bien formado
# =========================================================================


def test_phi_fields_exact_is_lowercase_only() -> None:
    """Match es case-insensitive — la constante debe estar en lowercase."""
    for field in PHI_FIELDS_EXACT:
        assert field == field.lower(), f"{field!r} no está en lowercase"


def test_phi_fields_exact_covers_obstetric_summary_identifiers() -> None:
    """Campos críticos del schema obstétrico están listados.

    Si el schema cambia y se introduce un identificador nuevo, ese campo
    DEBE sumarse a PHI_FIELDS_EXACT. Este test ancla el contrato actual.
    """
    must_include = {
        "nombre",
        "nombre_paciente",
        "dni",
        "numero_hc",
        "fecha_nacimiento",
        "direccion",
        "telefono",
        "email",
        "medico_tratante",
    }
    missing = must_include - PHI_FIELDS_EXACT
    assert not missing, f"PHI_FIELDS_EXACT no cubre: {missing}"


# =========================================================================
# Smoke combinado: payload realista de ObstetricSummary con PHI inyectado
# =========================================================================


def test_redact_phi_on_realistic_obstetric_summary_with_injected_phi() -> None:
    """Payload similar al output real del extractor, con PHI inyectado en
    campos donde podría filtrarse (notes_summary, metadata)."""
    payload = {
        # Identificación (PHI):
        "nombre_paciente": "Lucia Mendoza Quispe",
        "dni": "47812936",
        "fecha_nacimiento": "1995-04-12",
        # Clínicos (NO PHI — preservar):
        "patient_age": 30,
        "gestational_age_weeks": 16.4,
        "active_problems": ["Embarazo de bajo riesgo"],
        "lab_results": [
            {"name": "Hemoglobina", "value": "11.2", "unit": "g/dL"},
        ],
        "confidence_score": 0.94,
        # Notas con PHI inline:
        "notes_summary": "Paciente DNI 47812936 contacta al 987654321.",
    }
    result = redact_phi(payload)
    # PHI canónico redactado:
    assert result["nombre_paciente"] == REDACTED_MARKER
    assert result["dni"] == REDACTED_MARKER
    assert result["fecha_nacimiento"] == REDACTED_MARKER
    # Inline en notes_summary redactado:
    assert "47812936" not in result["notes_summary"]
    assert "987654321" not in result["notes_summary"]
    # Datos clínicos preservados:
    assert result["patient_age"] == 30
    assert result["gestational_age_weeks"] == 16.4
    assert result["active_problems"] == ["Embarazo de bajo riesgo"]
    assert result["lab_results"][0]["value"] == "11.2"
    assert result["confidence_score"] == 0.94


# =========================================================================
# Key-in-text detection (ADR-0009 actualización 2026-05-27)
# =========================================================================


from clinical_extractor.phi import _redact_phi_keys_in_text, _redact_string_content  # noqa: E402


def test_redact_key_nombre_with_equals() -> None:
    """``nombre=Maria Lopez`` → ``nombre=[REDACTED]`` (separator =)."""
    assert _redact_string_content("nombre=Maria Lopez") == f"nombre={REDACTED_MARKER}"


def test_redact_key_nombre_with_colon() -> None:
    """``nombre: Maria Lopez`` → ``nombre: [REDACTED]`` (separator :)."""
    assert _redact_string_content("nombre: Maria Lopez") == f"nombre: {REDACTED_MARKER}"


def test_redact_dni_with_key_in_text() -> None:
    """``dni: 47812936``: ambos caminos (DNI pattern + key-in-text) lo redactan.

    El DNI pattern fire primero sobre los 8 dígitos. Luego key-in-text
    procesa ``dni: [REDACTED]`` — el value ya es ``[REDACTED]``, así que
    el reemplazo es idempotente. Resultado: ``dni: [REDACTED]``.
    """
    assert _redact_string_content("dni: 47812936") == f"dni: {REDACTED_MARKER}"


def test_redact_multiple_keys_in_text() -> None:
    """Múltiples key-in-text en un mismo string se redactan todas."""
    input_text = "patient nombre=Maria dni=47812936 telefono=987654321"
    expected = (
        f"patient nombre={REDACTED_MARKER} dni={REDACTED_MARKER} "
        f"telefono={REDACTED_MARKER}"
    )
    assert _redact_string_content(input_text) == expected


def test_redact_phi_in_error_message_example() -> None:
    """Caso realista de mensaje de excepción con PHI mixto.

    "Failed for patient nombre=Maria Lopez DNI 47812936 control"

    Pipeline:
    1. DNI inline → "...DNI [REDACTED] control"
    2. key-in-text "nombre=" — el value captura hasta " DNI [REDACTED]"
       (lookahead detecta abreviación uppercase "DNI" como sentinela).
       Resultado del value: "Maria Lopez". Replace → "nombre=[REDACTED]".

    Final: "Failed for patient nombre=[REDACTED] DNI [REDACTED] control".
    """
    input_text = "Failed for patient nombre=Maria Lopez DNI 47812936 control"
    expected = f"Failed for patient nombre={REDACTED_MARKER} DNI {REDACTED_MARKER} control"
    assert _redact_string_content(input_text) == expected


def test_redact_does_not_affect_non_phi_keys() -> None:
    """Keys que NO son PHI (edad, gestational_age_weeks) pasan sin tocar."""
    input_text = "edad=28 gestational_age_weeks=24"
    assert _redact_string_content(input_text) == input_text


def test_redact_key_in_text_case_insensitive() -> None:
    """El match de la key es case-insensitive — preserva el case del input."""
    assert _redact_string_content("NOMBRE=Maria") == f"NOMBRE={REDACTED_MARKER}"
    assert _redact_string_content("Nombre: Maria") == f"Nombre: {REDACTED_MARKER}"


def test_redact_key_in_text_separator_variations() -> None:
    """El separator (incluyendo whitespace) se preserva en el output."""
    # Espacios alrededor del `=`.
    assert _redact_string_content("nombre =  Maria") == f"nombre =  {REDACTED_MARKER}"
    # Espacio antes del `:`, sin espacio después.
    assert _redact_string_content("nombre :Maria") == f"nombre :{REDACTED_MARKER}"


def test_redact_keys_in_nested_string_value() -> None:
    """En un dict con value string, la key-in-text aplica al value."""
    result = redact_phi({"error": "nombre=Maria"})
    assert result == {"error": f"nombre={REDACTED_MARKER}"}


def test_redact_phi_idempotent_with_key_in_text() -> None:
    """``redact_phi`` aplicada dos veces sobre key-in-text es estable."""
    x = "nombre=Maria Lopez"
    y = redact_phi(x)
    z = redact_phi(y)
    assert y == z
    assert y == f"nombre={REDACTED_MARKER}"


def test_redact_phi_preserves_clinical_data_after_key_in_text() -> None:
    """Estructuras clínicas grandes pasan sin cambio (sanity de no-rotura)."""
    payload = {
        "gestational_age_weeks": 24,
        "active_problems": ["DG"],
        "notes_summary": "Paciente con DG controlada",
        "metadata": {"version": "0.1.0"},
    }
    result = redact_phi(payload)
    assert result == payload


def test_key_in_text_with_value_longer_than_80_chars_does_not_redact() -> None:
    """Limitación documentada: si el value supera 80 chars sin un sentinela
    interno, el regex falla y el name NO se redacta.

    Trade-off aceptado en ADR-0009: preferimos all-or-nothing antes que un
    truncate parcial que pueda dejar el sufijo del nombre visible.
    """
    # >80 chars sin delimitador interno: solo nombres propios y conectivas
    # de 2-3 letras que no triggerean el lookahead [a-z]{4,}.
    very_long_name = (
        "Maria Lopez de la Torre del Valle Hidalgo de Espinoza del "
        "Castillo y Aragon de los Tres Reinos Sagrados"
    )
    input_text = f"nombre={very_long_name}"
    result = _redact_string_content(input_text)
    # El name pasa SIN redactar — limitación documentada.
    assert result == input_text, (
        "Cuando el value supera 80 chars sin sentinela, el redactor key-in-text"
        " falla y el name se preserva intacto"
    )


def test_key_in_text_redacts_url_query_param_with_phi() -> None:
    """URLs con PHI en query params SÍ se redactan — los URLs en logs son
    un vector real de leak."""
    input_text = "https://example.com/api?nombre=foo"
    expected = f"https://example.com/api?nombre={REDACTED_MARKER}"
    assert _redact_string_content(input_text) == expected


def test_email_pattern_still_works_after_integration() -> None:
    """Regresión: la integración con key-in-text no rompe el email pattern."""
    assert _redact_string_content("user maria@test.com") == f"user {REDACTED_MARKER}"


def test_key_in_text_does_not_match_inside_json_serialized_dict() -> None:
    """JSON serializado (con quote entre key y colon) NO matchea key-in-text.

    Razón: el separator pattern ``\\s*[=:]\\s*`` no tolera la quote
    inmediatamente después de la key. Los dicts Python/JSON se redactan
    vía la rama de ``isinstance(payload, dict)`` de ``redact_phi``, no
    vía la rama de ``isinstance(payload, str)``.
    """
    # String que representa un JSON serializado.
    input_text = '{"nombre": "Maria"}'
    # No matchea key-in-text porque después de "nombre" hay `"`, no `=` o `:`.
    assert _redact_string_content(input_text) == input_text


def test_key_in_text_helper_returns_string_unchanged_when_no_phi() -> None:
    """Sanity unit del helper directo: string sin PHI keys pasa sin cambio."""
    assert _redact_phi_keys_in_text("hello world") == "hello world"
    assert _redact_phi_keys_in_text("") == ""
    assert _redact_phi_keys_in_text("edad=28") == "edad=28"
