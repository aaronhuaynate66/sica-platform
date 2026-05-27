# 0009. PHI Redaction antes de Langfuse Cloud

- **Status:** Accepted — 2026-05-27 — Implementación bloqueante para primer PDF real
- **Date:** 2026-05-27
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** phi, redaction, privacy, ley-29733, langfuse, observability, regulatory
- **Related:** [ADR 0003](0003-security-and-phi-policy.md) (PHI policy general), [ADR 0007](0007-langfuse-observability.md) (Langfuse observability — punto de inyección), [ADR 0008](0008-prompt-registry-versioning.md) (formato ADR reciente)

## Context

- **Ley 29733 (Protección de Datos Personales, Perú)** aplica a SICA en todo procesamiento de datos personales de pacientes. Los outputs del extractor incluyen información identificable (nombre, DNI, fecha de nacimiento, dirección, número de HC) que califica como dato sensible bajo el art. 2 de la ley.
- **Langfuse Cloud (US region)** almacena cada trace en infraestructura externa. ADR 0007 § Privacidad y PHI marcó este punto como **trigger explícito** antes de procesar PHI real: "decidir entre BAA / self-hosted / output redacción / OTel custom".
- **Médico colaborador procesará el primer PDF real esta semana** (2026-05-27 a 2026-05-31). Sin redaction efectiva, cada trace deja PHI en US — exposición legal directa.
- **Self-hosted descartado en R1**: requiere infraestructura GCP/Render adicional (Postgres + S3 + ClickHouse), >USD 50/mes y 1-2 días de setup + mantenimiento continuo. Fuera del presupuesto y la ventana temporal.
- **BAA Enterprise descartado**: HIPAA aplica en US, no en Perú. Tier Enterprise de Langfuse Cloud >USD 200/mes. Innecesario para R1; reconsiderable en R3+ si se opera en mercados US.
- **El campo `output_json` del trace contiene el `ObstetricSummary` completo**: `notes_summary`, `lab_results[].value`, `active_problems` pueden contener nombre del paciente, DNI inline, edad gestacional exacta + fechas que permiten identificación.
- **El campo `metadata.pdf_filename`** propagado desde `apps/api` puede contener directamente el nombre del paciente (e.g. `historia_maria_lopez_2026.pdf`).
- **El `case_id`** derivado de `pdf_path.stem` puede contener identificadores en CLI / batch flows.

## Decision

**Redactar PHI ANTES de que el SDK Langfuse envíe payloads a Langfuse Cloud.** La redaction es una función pura en código local, ejecutada en el momento de construir el payload del SDK. Los datos completos siguen viviendo en memoria del extractor y en logs locales — sólo el envío a observability externa queda sanitizado.

### Campos a redactar (lista canónica)

Esta lista vive en `clinical_extractor/phi.py` como `PHI_FIELDS_EXACT`. Match case-insensitive sobre la key del payload.

- **Identidad personal**: `nombre`, `nombres`, `apellidos`, `nombre_completo`, `nombre_paciente`, `paciente_nombre`, `patient_name`, `first_name`, `last_name`, `full_name`.
- **Documentos de identidad**: `dni`, `cedula`, `documento`, `documento_identidad`, `identification`, `id_document`.
- **Historia clínica**: `numero_hc`, `hc_id`, `hc_numero`, `historia_clinica`, `medical_record_number`, `mrn`.
- **Contacto**: `direccion`, `address`, `telefono`, `phone`, `email`, `contacto`.
- **Médico tratante**: `medico_tratante`, `nombre_medico`, `cmp`, `doctor_name`, `physician_name`, `attending_physician`.
- **Establecimiento (cuando identificable)**: `establecimiento`, `establecimiento_salud`, `clinica`, `hospital`, `facility_name`.
- **Fecha de nacimiento exacta (riesgo de reidentificación)**: `fecha_nacimiento`, `fecha_de_nacimiento`, `date_of_birth`, `dob`, `birthdate`, `birth_date`.

### Campos que permanecen (no identifican por sí solos)

- `patient_age` (entero redondeado, sin DOB).
- `gestational_age_weeks`, `fum`, `fpp` (datos clínicos, no identifican; FUM/FPP pueden derivarse pero el riesgo es bajo en agregado).
- `active_problems`, `risk_factors`, `diagnosticos`, `plan_manejo`.
- `lab_results` (nombre del analito, valor, unidad, fecha — sin nombres de paciente).
- `confidence_score`, `evidence_spans`.
- IDs sintéticos: UUID, `request_id`, `operation_id`, `case_id` sanitizado.
- `notes_summary`: contenido narrativo. Se aplica redaction **por contenido** (patrones DNI/teléfono/email inline) pero no se borra completo — el output del modelo en este campo, por diseño del prompt actual, no debe contener PHI directo; cualquier filtración inline (e.g. el modelo copia un DNI desde el PDF) se neutraliza con el regex.

### Estrategia de reemplazo

- **Strings con key PHI**: reemplazo completo por `"[REDACTED]"`.
- **Listas con key PHI**: se reemplazan por `["[REDACTED]"]` si tenían contenido, `[]` si estaban vacías.
- **Strings con contenido PHI inline** (DNI/teléfono/email dentro de cualquier campo no listado): regex sub a `[REDACTED]`, preserva el resto del string.
- **Estructuras anidadas**: recursión.
- **Primitivos `int`, `float`, `bool`, `None`**: passthrough.

### Patrones de contenido inline

- **DNI peruano**: 8 dígitos consecutivos (`\b\d{8}\b`).
- **Teléfono móvil peruano**: 9 dígitos empezando en 9 (`\b9\d{8}\b`).
- **Email**: regex estándar (`\b[\w.-]+@[\w.-]+\.\w+\b`).

Estos patrones son **heurísticos conservadores**: pueden producir falsos positivos (códigos de 8 dígitos que no son DNI). Trade-off aceptado: preferimos sobre-redactar que dejar pasar.

### Filename sanitization

`metadata.pdf_filename` y `case_id` requieren tratamiento especial porque el filename puede contener el nombre del paciente directamente. La función `redact_filename`:

- Preserva filenames que comienzan con prefijos seguros conocidos (`synthetic_`, `longitudinal_lucia_`, `test_`, `fixture_`).
- Cualquier otro filename es reemplazado por `[REDACTED]{extension}`.

### Punto de inyección

Una función pura `redact_phi(payload) -> payload'` aplicada en:

1. **`clinical_extractor/tracing.py::trace_extraction`** — antes de pasar `output_json` y `metadata` a `client.start_observation(...)`.
2. **`sica_api/tracing.py::start_extract_trace`** y **`::finish_extract_trace`** — sobre metadata inicial (`pdf_filename` específicamente vía `redact_filename`) y `output_summary` al cerrar el span.

### Datos locales NO se redactan

- El return de `extract_from_pdf` mantiene datos completos para el caller (CLI, `apps/api`, futuros consumidores).
- Los logs locales (`logger.info`, telemetry JSON-line al stdout/archivo) NO usan los datos sanitizados — son herramienta de debugging y se manejan bajo otras políticas (RBAC sobre el host, no exfiltración).
- El response HTTP del endpoint `POST /extract` devuelve el JSON completo al cliente; la redaction solo aplica al SDK Langfuse.

## Consequences

### Positivas

- **Cumplimiento básico de Ley 29733** antes del primer PDF real, sin presupuesto adicional ni infraestructura nueva.
- **Costo cero**: una función pura más unos hooks. Implementación dentro de la ventana de esta semana.
- **Reversible**: si en futuro se contrata BAA o se levanta self-hosted, el redactor se desactiva con un flag y los traces vuelven a llevar payload completo. Ningún cambio destructivo de schema.
- **Logs locales preservan información completa** para debugging por caso: el médico colaborador o el founder pueden investigar un caso problemático con datos reales en el host, sin depender del dashboard Langfuse.
- **Tests anclan el contrato**: cualquier cambio futuro al schema que introduzca un campo PHI no listado en `PHI_FIELDS_EXACT` debe sumarse explícitamente — visible en el diff.
- **Doble cobertura**: redaction por key (exact match) + redaction por contenido (regex inline). Si el modelo filtra un DNI dentro de `notes_summary`, el regex lo neutraliza.

### Negativas

- **Dashboard Langfuse pierde información clínica útil para debugging por caso**: si una extracción se rompe para "la paciente Maria Lopez", el dashboard solo muestra `[REDACTED]`. Para investigar hay que cruzar `request_id` con logs locales.
- **Lista canónica de campos PHI debe mantenerse sincronizada con el schema**: drift posible si un futuro `ObstetricSummary` agrega `apellido_materno` y nadie lo suma a `PHI_FIELDS_EXACT`. Mitigación: tests + revisión en code review.
- **Heurísticas inline pueden producir falsos positivos**: un código de 8 dígitos que no es DNI (e.g. `12345678` como número de orden interno) se redacta. Aceptable en este contexto — la cantidad de información operacional perdida es marginal frente al riesgo regulatorio.
- **Heurísticas inline pueden producir falsos negativos**: un DNI escrito como `4781-2936` o con espacios no se detecta. Mitigación: el modelo del extractor no normaliza así por diseño; en práctica el riesgo es bajo. Auditoría externa pendiente para validar.
- **No reemplaza políticas relacionadas**: el redactor no resuelve consentimiento informado, encriptación en tránsito (ya cubierto por HTTPS del SDK), retención (Langfuse retiene por defecto X días — separar), ni RBAC sobre logs locales.

### Neutras

- **Performance**: la redaction es O(n) sobre el tamaño del payload. Para un `ObstetricSummary` típico (<5 KB JSON), el overhead es <1ms — invisible frente a los 15-20s de latencia del extractor.
- **El span padre en `apps/api`** ya llevaba un `output_summary` reducido (solo `confidence_score`, conteos, no detalle clínico — ver ADR 0007 § Trace context propagation). El redactor sobre ese span es defensivo: aunque el contenido sea poco, garantiza que si alguien agrega un campo futuro al summary, no se filtra.

## Alternativas consideradas

### Alternativa A: Langfuse self-hosted (DESCARTADO en R1)

**Forma**: Deploy del open-source de Langfuse en Render / GCP / on-prem partner. Datos nunca salen del perímetro controlado.

**Por qué no en R1**:
- Requiere stack adicional (Postgres + S3 + ClickHouse). En R1 tenemos exactamente 1 servicio en Render (`sica-api`) — sumar 3 más no se justifica hoy.
- Costo operacional: USD 20-50/mes + 1-2 días de bootstrap + mantenimiento continuo.
- La migración Cloud → self-hosted es trivial (mismo SDK, solo cambia `LANGFUSE_BASE_URL`). Diferimos el costo.

**Cuándo reconsiderar**: cuando aparezca presupuesto formal de partner clínico (R2+), cuando el volumen de traces supere el tier free de Cloud (>50k events/mes), o cuando un partner exija ubicación de datos en Perú.

### Alternativa B: BAA con Langfuse Cloud Enterprise (DESCARTADO)

**Forma**: contratar tier Enterprise con BAA firmado.

**Por qué no**:
- HIPAA es un marco US — un BAA bajo HIPAA no satisface directamente Ley 29733 peruana, aunque sus controles técnicos sean equivalentes.
- Tier Enterprise >USD 200/mes. Innecesario en R1.
- Aunque firmáramos, el dato igual reside físicamente en US — análisis legal independiente requeriría revisar si transferencia internacional está autorizada bajo el contrato peruano correspondiente.

**Cuándo reconsiderar**: si SICA opera en mercados US (R3+), o si la ANPD peruana emite reglamento que reconozca BAA US como salvaguarda equivalente.

### Alternativa C: Pseudonimización con tabla de mapeo (DESCARTADO)

**Forma**: reemplazar nombre/DNI por tokens (e.g. `PATIENT-A4F2`) y mantener una tabla local que mapea token → identidad real.

**Por qué no**:
- La tabla de mapeo se convierte en un nuevo repositorio PHI sensible que hay que proteger, respaldar, controlar acceso, eliminar bajo derecho de supresión. Complejidad operacional que no aporta sobre el simple `[REDACTED]`.
- Solo gana valor si necesitamos correlacionar traces específicos de Langfuse con pacientes reales — caso que se resuelve mejor con `request_id` + logs locales.

### Alternativa D: Cifrado simétrico con clave externa (DESCARTADO)

**Forma**: cifrar los valores PHI antes de enviar a Langfuse usando una clave que vive solo en SICA. Langfuse almacena ciphertext.

**Por qué no**:
- Si Langfuse Cloud es comprometido, atacante puede pedir descifrado a SICA — el problema regulatorio sigue siendo "PHI está en US codificado", no "PHI está en US en plano".
- Complejidad de gestión de claves sin beneficio incremental sobre redaction.
- Pierde la utilidad del dashboard (datos ilegibles para revisión humana).

### Alternativa E: Flag `LANGFUSE_INCLUDE_OUTPUT=false` (mencionada en ADR 0007)

**Forma**: simplemente omitir el `output_json` del trace, sin redactar campo por campo.

**Por qué redaction es mejor**:
- Preserva los campos clínicos no-PHI (`active_problems`, `gestational_age_weeks`) que SÍ son útiles para debugging operacional (¿el modelo está extrayendo problemas razonables?).
- Cubre además `metadata.pdf_filename` y el contenido inline que el flag no toca.

Compatibles entre sí: si en futuro se decide omitir output completo, el redactor sigue protegiendo metadata.

## Implementación R1 (esta sesión)

- **Módulo nuevo**: `services/clinical-extractor/src/clinical_extractor/phi.py` con `redact_phi`, `redact_filename`, constante `PHI_FIELDS_EXACT`, patrones de contenido.
- **Hook en `clinical_extractor/tracing.py`**: sanitización de `output_json` + `metadata` antes de `client.start_observation`.
- **Hook en `apps/api/src/sica_api/tracing.py`**: sanitización en `start_extract_trace` (filename + user_metadata) y `finish_extract_trace` (output_summary).
- **Tests unitarios**: ≥15 cubriendo recursión, idempotencia, pureza, case-insensitive, primitivos, estructuras vacías, filename sanitization.
- **Tests de integración con tracing**: mocks del SDK Langfuse verifican que el payload enviado contiene `[REDACTED]` en campos PHI y que el return de `extract_from_pdf` sigue completo.
- **Smoke test contra Anthropic real**: 1 caso `longitudinal_lucia_sem16.pdf` (~USD 0.04). Verificación visual en dashboard.

## TODOs R2+

- **Auditoría externa del redactor**: pen-test que intente filtrar PHI mediante prompts adversariales o filenames maliciosos.
- **Política de consentimiento informado**: independiente del redactor, requiere flujo con paciente y registro auditable. Fuera del scope de este ADR.
- **Política de retención de traces en Langfuse**: el redactor reduce el riesgo pero los traces igual se guardan N días. Decidir período máximo y mecanismo de borrado automatizado.
- **Considerar self-hosted** si crece tráfico (>50k events/mes) o si un partner exige residencia de datos en Perú.
- **Hooks de CI** que escaneen `PHI_FIELDS_EXACT` contra `ObstetricSummary` y rompan el build si un campo nuevo del schema no está clasificado.

## Referencias

- **Ley 29733** — Ley de Protección de Datos Personales del Perú. Reglamento DS 003-2013-JUS.
- **ADR 0003** — Security and PHI handling policy (predecesor genérico).
- **ADR 0007** — Langfuse observability (define el punto de inyección y abre explícitamente la pregunta de qué hacer con PHI en cloud).
- **ADR 0008** — Prompt Registry (formato ADR seguido aquí).
- **[`docs/operations/phi-handling.md`](../operations/phi-handling.md)** — Guía operacional que traduce este ADR a procedimientos concretos para desarrolladores y médicos colaboradores: checklist antes del primer PDF real, cómo identificar paciente desde un trace, comportamiento de filenames, limitaciones conocidas.
- **STRATEGY § 11.1, § 13** — PHI sensible nunca sale a cloud sin política explícita.
- **Commits asociados** — pendientes en esta sesión: ADR + implementación + tests.

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- **Aparece presupuesto/partner para self-hosted** → reconsiderar y posiblemente desactivar el redactor (con tests que validen reversibilidad).
- **El schema de `ObstetricSummary` cambia** → revalidar que `PHI_FIELDS_EXACT` cubre los nuevos campos.
- **ANPD emite guidance específico sobre observability LLM en healthtech** → adaptar lista canónica.
- **Auditoría externa identifica filtración** → reforzar patrones o cambiar estrategia.
- **R3+ con tráfico cross-border (mercados US)** → reconsiderar BAA Enterprise.

Hasta entonces, **redaction local antes del SDK Langfuse** es la configuración operativa.

## Migration log

| Fecha | Cambio | Autor | ADR superseder |
|---|---|---|---|
| 2026-05-27 | Creación inicial | Aaron Huaynate | — |
| 2026-05-27 | Agregada detección de keys PHI en texto plano (`_redact_phi_keys_in_text`). Ver sección "Actualización 2026-05-27 — Detección de keys PHI en texto plano" abajo. | Aaron Huaynate | — |

## Actualización 2026-05-27 — Detección de keys PHI en texto plano

### Contexto

El sanitizer original (`_redact_string_content`) cubría dos clases de PHI:

1. **Patterns inline** sobre strings: DNI peruano, móvil peruano, email.
2. **Keys PHI en dicts** vía `redact_phi` recursivo.

Faltaba una tercera clase: **keys PHI con valor en texto plano** dentro de strings. Mensajes de excepción de providers y logs estructurados pueden serializar PHI como `"nombre=Maria Lopez"` o `"dni: 47812936 patient"` — ese formato escapaba al sanitizer porque la "key" no es key de dict sino texto adyacente a su valor.

El TODO #3 del commit `5fc1c95` documentó este agujero explícitamente: "Maria Lopez puede pasar — la clave nombre solo se detecta cuando es key de un dict". Cerrar este agujero antes del primer PDF real es bloqueante.

### Cambio

Agregada función nueva `_redact_phi_keys_in_text(text)` en `clinical_extractor/phi.py`:

- Regex construida una sola vez al import-time con la alternancia completa de `PHI_FIELDS_EXACT` ordenada por longitud descendente (matchear "nombre_paciente" antes que "nombre" para evitar partial matches).
- Case-insensitive **solo** para la key (vía `(?i:...)` scope-limited) — el resto del pattern es case-sensitive para que las heurísticas de uppercase del lookahead funcionen.
- Value capturado con cap de 80 chars máx (no-greedy).
- Lookahead define dónde para de capturar el value:
  1. Delimitador (`,;)}\n`).
  2. Whitespace + palabra lowercase 4+ chars (con tildes).
  3. Whitespace + abreviación uppercase 2+ chars seguida de `\s`/`=`/`:`/`$` (captura sentinelas como `DNI`, `HC`).
  4. Whitespace + otra key PHI seguida de separador.
  5. Fin de string.

Integrada en `_redact_string_content` después de los patterns inline. Orden importa:

1. Patterns inline primero (cubren PHI suelto: `"failed lookup of 47812936"`).
2. Key-in-text después (cubre PHI contextual: `"nombre=Maria"`).

### Casos cubiertos

| Input | Output |
|---|---|
| `nombre=Maria Lopez` | `nombre=[REDACTED]` |
| `nombre: Maria Lopez` | `nombre: [REDACTED]` |
| `Failed for patient nombre=Maria Lopez DNI 47812936 control` | `Failed for patient nombre=[REDACTED] DNI [REDACTED] control` |
| `patient nombre=Maria dni=47812936 telefono=987654321` | `patient nombre=[REDACTED] dni=[REDACTED] telefono=[REDACTED]` |
| `NOMBRE=Maria` (case-insensitive) | `NOMBRE=[REDACTED]` |
| `nombre =  Maria` (espacios variables) | `nombre =  [REDACTED]` |
| `https://example.com/api?nombre=foo` (URL en log) | `https://example.com/api?nombre=[REDACTED]` |

### Casos NO cubiertos (limitaciones residuales documentadas)

1. **NER (Named Entity Recognition) no implementado**. Nombres mencionados sin key explícita pasan: `"la paciente Maria Lopez no presenta anemia"` → mismo string sin redactar. Aceptable para R1 porque el riesgo es bajo en contexto técnico (errores de SDK no suelen narrar prosa con nombres). Revisar si emerge necesidad operacional.

2. **Values muy largos (>80 chars) sin delimitador interno**. La regex es all-or-nothing: si el lookahead no triggerea dentro del cap de 80 chars, el match completo falla y el name se preserva. Trade-off aceptado: preferimos texto sin redactar (mensaje claro) que truncate parcial que filtre el sufijo del nombre.

3. **JSON serializado como string** (`'{"nombre": "Maria"}'`). La quote entre key y `:` rompe el separator pattern. Esto NO es un agujero real porque dicts Python/JSON reales (no serializados como string) se redactan vía la rama `isinstance(payload, dict)` de `redact_phi`.

### Tests

- **14 unit tests nuevos** en `services/clinical-extractor/tests/test_phi.py` cubriendo: separator `=`/`:`, múltiples keys en una sola línea, case-insensitive, variaciones de whitespace, keys no-PHI preservadas, idempotencia, dict con value string, payload clínico realista, value >80 chars (limitación), URLs con PHI, regresión de email, JSON serializado, sanity unit del helper directo.
- **2 integration tests nuevos** en `apps/api/tests/test_phi_in_error_responses.py` cubriendo: unit del helper `_safe_provider_error_detail` con key-in-text, E2E via TestClient para 503 con `nombre=Maria Lopez DNI 47812936`.

### Compat

- `redact_phi` y `redact_filename` mantienen el contrato público sin cambios.
- Tests pre-existentes: 24 originales de `test_phi.py` + 13 originales de `test_phi_in_error_responses.py` siguen verdes sin modificación.
- `_redact_string_content` ahora compuesta de dos capas; el orden (inline → key-in-text) garantiza idempotencia: aplicar dos veces da el mismo resultado.
