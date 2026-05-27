# Manejo de PHI en SICA — Guía operacional

> **Documento operacional, no normativo.** La política está en [ADR-0009](../decisions/0009-phi-redaction-in-tracing.md). Este documento traduce esa política a procedimientos concretos para desarrolladores y médicos colaboradores que van a procesar PDFs reales.
>
> Audiencia: cualquiera que despache un request a `POST /extract` con un PDF de paciente real, o investigue un trace problemático en Langfuse Cloud.

---

## TL;DR

- **SICA redacta PHI antes de enviarlo a Langfuse Cloud.** El dashboard externo muestra `[REDACTED]` en campos identificables.
- **Datos locales son completos.** Los logs del host, el return de `extract_from_pdf` y el response HTTP al cliente NO se redactan.
- **El dashboard de Langfuse NO es fuente de verdad clínica.** Para investigar un caso específico, ir a los logs locales.

---

## Estado del sistema

| Capa | PHI presente | Cómo |
|---|---|---|
| Return de `extract_from_pdf` (memoria del extractor) | ✅ Completo | Sin sanitización — el caller decide qué hacer |
| Response HTTP de `POST /extract` (al cliente) | ✅ Completo | El cliente recibe el `ObstetricSummary` íntegro |
| Logs locales (`logger.info`, telemetry JSON-line a stdout) | ✅ Completo | Sin redacción — herramienta de debugging |
| Langfuse Cloud (US region) — span padre y generation | ❌ Redactado | `redact_phi` aplicado a output_json + metadata antes del SDK |
| HTTP error responses (400 / 500 / 503) | ❌ Redactado | `_safe_provider_error_detail` aplica `redact_phi` sobre mensajes de excepción |

**Cumplimiento**: básico para Ley 29733 (Perú). NO sustituye consentimiento informado ni DPA con el partner.

---

## Antes del primer PDF real — checklist

Esta lista vive aquí porque el contexto se olvida; debe correrse mentalmente cada vez que el equipo procese un PDF real por primera vez en un entorno nuevo.

1. **Validar visualmente que el dashboard Langfuse no muestra PHI.**
   - Subir un PDF de prueba (puede ser `synthetic_case_01.pdf`).
   - Esperar 30 segundos.
   - Abrir el trace en Langfuse Cloud → expandir `output` y `metadata`.
   - Confirmar: nombres / DNIs / fechas de nacimiento aparecen como `[REDACTED]`.
   - Si **algún campo PHI no está redactado**, NO procesar PDFs reales — abrir issue y revisar `clinical_extractor/phi.py::PHI_FIELDS_EXACT`.

2. **Confirmar el entorno de Langfuse en Render.**
   - En Render → service `sica-api` → Settings → Environment vars.
   - Verificar `LANGFUSE_TRACING_ENVIRONMENT=production`.
   - Si está vacío o `development`, los traces reales del API caerán en el dashboard equivocado (no hay data loss, sí hay confusión). Ver [ADR-0007 § actualización 2026-05-26 default environment](../decisions/0007-langfuse-observability.md).

3. **Verificar que los logs locales preservan información completa.**
   - En Render → Logs → buscar el último `extract ok` o `extract failed`.
   - Confirmar que `request_id` aparece y que el `uploaded_filename` original es legible.
   - Si los logs están truncados o rotados antes de las 24 h, considerar persistencia adicional antes del próximo caso real.

4. **Establecer protocolo de consentimiento informado con la paciente.**
   - Independiente del redactor. El consentimiento debe ser explícito, registrado y verificable.
   - Por ahora el founder/médico colaborador documenta el consentimiento por fuera del sistema. Migrar a flujo automatizado cuando exista el frontend de captura.

5. **Validar el filename antes de subir.**
   - Si el filename del PDF contiene nombre/DNI (e.g. `historia_maria_lopez_2026-05-27.pdf`), renombrar a un alias seguro (e.g. `caso_2026-05-27.pdf`) antes del upload.
   - Razón: el filename original queda visible en **logs locales del API** (no se redacta allí), aunque en Langfuse Cloud sí se reemplaza por `[REDACTED].pdf`.

---

## Cómo identificar a una paciente desde un trace problemático

Si un trace en Langfuse muestra `confidence_score=0.4`, un error, o cualquier anomalía que requiera investigación clínica:

1. **En el dashboard de Langfuse**, anotar el `request_id` del trace (visible en metadata).
2. **Abrir logs locales del host**:
   - **Producción (Render)**: dashboard de Render → `sica-api` → Logs → buscar por `request_id`. Los logs estructurados incluyen `uploaded_filename` y `provider`.
   - **Local**: `stdout` del proceso de `uvicorn sica_api.main:app` o el archivo configurado en `LOG_*` env vars. El telemetry JSON-line del extractor sale por stderr.
3. **Cruzar `request_id` → `uploaded_filename` → identidad de paciente** vía registros del médico colaborador (lista de uploads, hoja de caso por caso).
4. **Si los logs locales se rotaron** y no encontrás el `request_id`, esa información se perdió. Esto es un riesgo operacional conocido — antes del próximo caso real, agregar persistencia de logs (Render Disks, log shipper a un destino con retención más larga).

---

## Filenames de upload — tabla de comportamiento

| Patrón del filename | En el dashboard Langfuse | En logs locales |
|---|---|---|
| `synthetic_*.pdf` | Preservado | Preservado |
| `longitudinal_lucia_*.pdf` | Preservado | Preservado |
| `test_*.pdf` | Preservado | Preservado |
| `fixture_*.pdf` | Preservado | Preservado |
| **Cualquier otro** (e.g. `historia_paciente.pdf`) | `[REDACTED].pdf` | Preservado |

**Implicación práctica**: si el médico sube `historia_maria_lopez_2026-05-27.pdf`, ese filename:

- Queda en el log del API en Render (sin redacción).
- Sale como `[REDACTED].pdf` en el dashboard Langfuse.

Para evitar exposición en logs:

- **Hoy**: renombrar antes de subir. Convención propuesta: `caso_{fecha}_{secuencial}.pdf`.
- **Cuando exista frontend**: el cliente del frontend debe sanitizar el filename antes del `POST` multipart.

---

## Qué hacer si necesitas desactivar la redacción

Cuando exista BAA con Langfuse Enterprise, self-hosted, o cambio regulatorio que lo justifique:

1. **NO desactivar sin actualizar [ADR-0009](../decisions/0009-phi-redaction-in-tracing.md)** y confirmar implicaciones regulatorias con asesor externo.
2. Para desactivar quirúrgicamente:
   - Comentar los hooks `redact_phi(...)` en `services/clinical-extractor/src/clinical_extractor/tracing.py`.
   - Comentar los hooks `redact_phi(...)` en `apps/api/src/sica_api/tracing.py`.
   - Comentar los hooks en `apps/api/src/sica_api/routes/extract.py` (helper `_safe_provider_error_detail` y echo del query param / content-type).
3. El módulo `services/clinical-extractor/src/clinical_extractor/phi.py` queda como código muerto seguro hasta una decisión formal.
4. Revertir los tests que anclan el comportamiento de redacción si la política cambia.

---

## Política de retención de traces

**Hoy (R1)**: traces se guardan en Langfuse Cloud por su retención default (no auditado).

**TODO R2** ([ADR-0009 § TODOs R2+](../decisions/0009-phi-redaction-in-tracing.md)):

- Definir período máximo de retención (e.g. 30 días, alineado con Ley 29733 y derecho de supresión).
- Implementar mecanismo automatizado de borrado vía Langfuse API (cron job o action manual al cierre de cada sesión clínica).
- Documentar el procedimiento de borrado para responder solicitudes de derecho de supresión del titular.

---

## Limitaciones conocidas

1. **Drift schema vs `PHI_FIELDS_EXACT`.** Si el `ObstetricSummary` (o cualquier otro schema en `clinical_extractor/schemas.py`) agrega un campo PHI nuevo, debe sumarse a `PHI_FIELDS_EXACT`. El test `test_phi_fields_exact_covers_obstetric_summary_identifiers` ancla los campos críticos actuales, pero **no detecta nuevos automáticamente**. Mitigación R2: hook de CI que escanee el schema y rompa el build si un campo nuevo no está clasificado.

2. **Patrones inline conservadores.** El regex DNI captura **cualquier secuencia de 8 dígitos**, no solo DNIs reales (e.g. un código interno de 8 dígitos también se redacta). Aceptable — preferimos sobre-redactar.

3. **Falsos negativos del regex.** Un DNI escrito como `4781-2936` o con espacios no matchea el pattern actual. En la práctica el modelo del extractor no normaliza así; auditoría externa pendiente para validar.

4. **Error messages en responses HTTP.** El sanitizer aplica `redact_phi` sobre patterns inline (DNI, teléfono, email). Si un mensaje de excepción tiene un campo con clave PHI dentro del string (e.g. `"Failed for patient nombre=Maria"`), la palabra "Maria" puede pasar — la clave `nombre` solo se detecta cuando es key de un dict, no cuando es texto plano. Mejora pendiente para R2 si emerge el caso.

5. **Logs locales NO se redactan.** Acceso a logs del host es equivalente a acceso a PHI. Tratar logs como información sensible:
   - No exportar logs a sistemas externos sin política de retención + control de acceso.
   - No publicar transcripts de log en chats / tickets sin sanitización manual.
   - Configurar rotación + retención corta cuando se procesen PDFs reales.

6. **Filenames PHI en logs.** Como se documenta arriba, el filename del upload aparece sin redactar en logs del API. El frontend debe sanitizar; hasta entonces, el operador del upload debe renombrar manualmente.

---

## Procedimiento de auditoría externa (TODO R2)

Antes de exponer SICA a un partner clínico formal o procesar volumen significativo de PDFs reales:

- **Pen-test del redactor** con prompts adversariales: PDFs que intenten inyectar PHI en campos no-listados, filenames con encoding malicioso, content-types con PHI inline.
- **Auditoría manual** de una muestra de 20-50 traces reales para verificar que el redactor cubrió todos los campos PHI esperados.
- **Reporte firmado** del auditor que ancle el estado del redactor en una fecha específica.

---

## Referencias

- [ADR-0003](../decisions/0003-security-and-phi-policy.md) — Política PHI general.
- [ADR-0007](../decisions/0007-langfuse-observability.md) — Langfuse Cloud (punto de inyección del redactor).
- [ADR-0009](../decisions/0009-phi-redaction-in-tracing.md) — Decisión normativa del redactor.
- [`docs/security/data-handling.md`](../security/data-handling.md) — Política operativa de PHI más amplia.
- [`docs/security/ley-29733-compliance.md`](../security/ley-29733-compliance.md) — Mapeo a Ley 29733 con bloqueantes.

---

## Cambios

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-05-27 | Creación inicial. Captura los 5 puntos operacionales identificados al cierre de la sesión de implementación del redactor. | Aaron Huaynate |
