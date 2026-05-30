# Estado de SICA — snapshot manual

> Este documento es un snapshot manual del estado del programa, complementario al `MASTER_PLAN.md` auto-generado (sync desde issues de GitHub).
>
> Usar este archivo para registrar contexto que NO se captura por estado de issues: decisiones implementadas, pendientes de activación, criterios de promoción, etc.

---

## Estado R1 al 2026-05-29

### Cerrado esta semana (técnico)

- **ADR-0008**: Prompt registry versionado con hash inmutable (Fase 1).
- **ADR-0009**: PHI redaction antes de Langfuse Cloud (cumplimiento Ley 29733). Sanitizer extendido con detección de keys en texto plano (`nombre=Maria` → `nombre=[REDACTED]`).
- **ADR-0010**: Política de retención Langfuse 180 días + cleanup automatizado (workflow scheduled dry-run + workflow_dispatch manual).
- **ADR-0011**: Frontend Next.js + Supabase + Vercel.
- **Provider routing en `apps/api`**: query param `?provider=anthropic|vertex` enruta al provider explícito (paridad con CLI).
- **CLI `--prompt-version`**: flag para forzar versión específica de `extract_obstetric` desde el extractor CLI.
- **Sanitizer key-in-text**: detección de PHI en strings serializados (mensajes de excepción de providers, logs).
- **Prompt `extract_obstetric_v2`**: corrige el bug "embarazo de N semanas en active_problems" reclasificándolo como contexto cronológico.
- **Comparator offline de prompts**: paquete `evals/src/sica_evals/comparators/prompt_*.py` + CLI `sica-eval compare-prompts`. Veredicto sobre el dataset Lucía v1 vs v2: **YELLOW** (no autoriza promoción automática).
- **Mypy strict obligatorio en CI**: removido `|| true` del step Mypy en `.github/workflows/ci.yml`.
- **Hash anchor para TODAS las versiones de prompt**: `KNOWN_PROMPT_HASHES` cubre v1 + v2; tests adicionales detectan ediciones in-place y prompts sin anclar.
- **Dataset longitudinal Lucía Mendoza Quispe**: 4 PDFs sintéticos validados (sem16, sem24, sem32, sem38) con escenario completo de diabetes gestacional.
- **Frontend SICA completo**: auth (magic link), upload PDF, vista paciente longitudinal, comparador side-by-side, integración con metadata del extractor.

### Pendiente activación (acción manual mañana)

Ver [docs/operations/activation-playbook-2026-05-29.md](operations/activation-playbook-2026-05-29.md). Tiempo estimado: 25–35 min.

- Crear proyecto Supabase `sica-platform` (5 min).
- Aplicar migration SQL (`supabase/migrations/0001_initial_schema.sql`) — 2 min.
- Configurar Supabase Auth + Site URL + Redirect URLs — 3 min.
- Agregar 4 env vars a Vercel proyecto `sica-web` — 5 min.
- Agregar 3 secrets de GitHub Actions para workflow `langfuse-cleanup` — 3 min.
- Smoke E2E con dataset Lucía (sem16 + sem24 + timeline + comparador) — 10 min.

### Pendiente R1 (código)

- **Promover prompt `v2` → default** en `DEFAULT_VERSIONS` de `clinical_extractor.prompts.registry`. Requiere revisión clínica del veredicto YELLOW del comparator (no es promoción automática).
- **Telemetría sanitizer match-rate**: instrumentar `_redact_string_content` para registrar cuántas redacciones ocurren por categoría (inline DNI vs móvil vs email vs key-in-text). Útil para detectar drift del modelo.
- **`apps/api` con `--prompt-version` query param**: paridad con la CLI, hoy solo el extractor CLI soporta override de versión.
- **`apps/api` a `PKG_DIRS` del lint-python workflow**: ya pasa `mypy --strict` localmente (0 errores), no está incluido en CI aún. Extender `PKG_DIRS` en `.github/workflows/ci.yml`.
- **Actualizar índice de ADRs cuando se agregue uno nuevo**: hábito operacional, no técnico — sumar fila a la tabla de `docs/decisions/README.md` en el mismo commit que crea el ADR.

### Pendiente R1 (no-código)

- **Conversación operacional con médico colaborador**: convención de filenames (no PHI), correlación trace → paciente real (request_id + logs locales), interpretación de `confidence_score`.
- **Consentimiento informado con paciente**: documento físico/digital firmado, registro auditable separado del sistema.
- **Validación de rotación de logs locales en Render**: confirmar que persisten ≥48h para investigar casos problemáticos.
- **Convención de renombrado de PDFs**: alias seguros (`caso_{fecha}_{secuencial}.pdf`) antes de subir, hasta que el frontend sanitize el filename del upload.

### Bloqueado externamente

- **#12 MedGemma 4B**: bloqueado por activación de GCP billing para el partner. Hasta entonces, Claude Sonnet vía Anthropic es el único provider activo.
- **#1 Regulatorio** (clasificación software asistivo no dispositivo médico).
- **#2 Ley 29733** (banco DPIA + DPO + consentimientos).
- **#3 Marca Indecopi**.
- **#4 Partner fundador clínico**.
- **#5 150–200 historias obstétricas desidentificadas para R0**.

### Roadmap R2+

- **DIGEMID compliance** (registros médicos).
- **Asesor legal Ley 29733** dedicado.
- **Marca Indecopi** registrada.
- **Partner fundador** confirmado (clínica privada materno-infantil Lima).
- **Dataset real**: 150–200 historias clínicas con review humano.
- **5 KOLs identificados** y onboarded.
- **Análisis competitivo** Perú/LatAm con field research.
- **NER para PHI sin key**: nombres mencionados sin `nombre=` (e.g. "la paciente Maria Lopez no presenta...") — limitación residual documentada en ADR-0009.
- **Self-hosted Langfuse o BAA Enterprise**: si emerge volumen o partner exige residencia en Perú.
- **Document classification multi-tipo**: control prenatal vs eco vs lab, hoy un solo schema.

---

## Decisiones pendientes (no de código)

### Promoción prompt `extract_obstetric` v2 → default

Estado: **bloqueado por veredicto YELLOW** del comparator offline (`evals/src/sica_evals/comparators/prompt_comparator.py`).

Lecturas:
- El veredicto sobre el dataset Lucía: 0 regresiones detectadas, 0 mejoras formalmente categorizadas, cambios mayoritariamente neutrales en reclasificación entre `active_problems` y `risk_factors`. Identidad cronológica (edad, FUM, FPP, GA) preservada en 4/4 controles.
- El comparator es conservador por diseño — un YELLOW dice "requiere revisión clínica humana" no "rechazar".
- La decisión de promover requiere validación del médico colaborador sobre algún caso real, no sintético.

Recomendación: esperar al smoke E2E del médico para tener al menos 1–2 casos reales y entonces revisar el diff de outputs entre v1 y v2.

---

## Migration log

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-05-29 | Creación inicial. Captura el snapshot de cierre de la semana de implementación R1. | Aaron Huaynate |
