# 0006. Render Dashboard UI tiene precedencia sobre `render.yaml`

- **Status:** Accepted
- **Date:** 2026-05-25
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** infra, deploy, render, deuda-tecnica, postmortem
- **Related:** [ADR 0001](0001-monorepo-turborepo.md) (monorepo — origen del problema de paths cross-package), `apps/api/RENDER.md`, `render.yaml`

## Context

El 25 de mayo de 2026, al deployar el endpoint `GET /providers` (commit `9606b8d`) sobre `apps/api`, descubrimos accidentalmente un bug pre-existente **desde el 22 de mayo** (primer push del API a Render) que había estado degradando producción en silencio.

**Síntoma observado.** `/providers` en producción devolvía `{"providers": [], "total_providers": 0, ...}` en lugar del shape esperado con 2 providers (`anthropic`, `vertex-medgemma`). El endpoint `/models` retornaba los 9 ítems de la política estática pero con `is_available=false` y `provider_id=null` en todos. El endpoint `/health` reportaba `extractor_available: true`.

**Causa raíz.** El paquete `clinical_extractor` (workspace local, no PyPI) nunca había sido instalado en el entorno de Render. Las rutas que dependen del extractor caían silenciosamente al `except ImportError`:

- `/providers` → respuesta vacía con HTTP 200.
- `/models` → política estática sin runtime state.
- `/extract` → habría fallado con 500 al primer request real (pero `/extract` nunca se había probado end-to-end contra producción).

**Cómo se descubrió que `render.yaml` era ignorado.** El `render.yaml` del repo declaraba explícitamente:

```yaml
buildCommand: pip install --upgrade pip && pip install -e .
```

Es decir, **el yaml mismo nunca había instalado el extractor**. Cuando agregamos `pip install -e ../../services/clinical-extractor` al `buildCommand` (`22cfbab`) y pusheamos, esperando que `autoDeploy: true` hiciera el resto, observamos que:

1. `/health` cambiaba comportamiento a la nueva lógica (`extractor_available: false` por `AND` con import check) → confirmando que **el código nuevo SÍ se estaba deployando**.
2. `/providers` seguía vacío y `/models` seguía sin runtime state → confirmando que **el `buildCommand` de `render.yaml` NO se estaba ejecutando**.

Tres intentos sucesivos de amend + force-push (`dea3ad9`, `da53220`, `1483dc6`) con `buildCommand` cada vez más robustos (sin `-e`, con sanity check `python -c "import clinical_extractor"`, con `set -e`, con paths via `$PWD`, sin `pushd`/`popd` para ser `sh`-compatible) **no produjeron ningún cambio observable** en producción durante ~50 minutos de polling.

Investigación manual en el dashboard de Render reveló que **había un `buildCommand` viejo hardcodeado en la UI del servicio** desde el primer deploy del 22 de mayo. Render aplica el siguiente orden de precedencia:

> **Dashboard UI > render.yaml (Blueprint)**

Mientras hubiera un valor en el campo Build Command de la UI, Render usaba ese valor e **ignoraba completamente el `buildCommand` declarado en `render.yaml`**.

**Fix temporal aplicado.** Editamos el campo Build Command en la UI de Render con:

```sh
pip install --upgrade pip && pip install /opt/render/project/src/services/clinical-extractor && pip install -e .
```

Path absoluto `/opt/render/project/src/...` (la ruta canónica donde Render monta el checkout). Trigger de Manual Deploy. En ~3 minutos, producción correctamente reportó:

- `/health` → `extractor_available: true`
- `/providers` → `total_providers: 2, available_count: 1` con anthropic operativo y vertex-medgemma con nota explicativa.
- `/models` → 9 ítems con `is_available=true` y `provider_id="anthropic"` para los modelos Claude.

**Por qué no se detectó antes.** Hasta esta sesión, ningún endpoint del API leía dinámicamente del registry del extractor:

- `/health` solo verificaba la env var `ANTHROPIC_API_KEY`. Con la key presente en Render UI, siempre reportaba `true`.
- `/models` retornaba la política estática (hardcoded en `routes/models.py`); los campos `is_available` y `provider_id` eran metadata adicional **opcional**. Que aparecieran como `false`/`null` se podía interpretar como "el provider no se registró todavía" — comportamiento aceptable en R0 según el comentario del módulo.
- `/extract` requiere multipart con PDF real; nadie había hecho un smoke contra prod más allá de `/health`.

El endpoint `/providers`, por diseño, **expone el shape completo** y se rompe ruidosamente si el registry está vacío. Por accidente, actuó como **el primer health-check end-to-end real** del API en producción.

## Decision

**Por ahora, el `buildCommand` de producción vive en la UI de Render con path absoluto, no en `render.yaml`.** El archivo `render.yaml` queda como **decoración referencial** hasta que se vacíe explícitamente el campo de UI en una sesión futura controlada.

Razones para no vaciar la UI ahora:

1. **Producción quedó funcional inmediatamente.** Cambiar la fuente de verdad mientras está sirviendo correctamente introduce riesgo de regresión sin beneficio inmediato.
2. **Sesión actual ya consumió alta atención.** Vaciar la UI requiere validación post-deploy completa (`/health`, `/providers`, `/models`, `/extract` con PDF real). Mejor en sesión dedicada con tiempo holgado.
3. **Path absoluto en UI es más legible para debug.** Si en el futuro alguien abre la UI de Render para ver qué se está corriendo, el valor literal `/opt/render/project/src/services/clinical-extractor` es directo. Una indirección a `render.yaml` requiere recordar la jerarquía de precedencia.

Estado declarativo del repo:

- `render.yaml` mantiene el `buildCommand` correcto (con path absoluto equivalente al de la UI) para que **si alguna vez se vacía el campo de UI, el comportamiento sea idéntico**. Es snapshot honesto, no aspiracional.
- Un comentario en `render.yaml` advierte sobre la precedencia de UI y referencia este ADR.
- `apps/api/RENDER.md` documenta el procedimiento de "vaciar UI + verificar yaml" como **runbook futuro**.

## Consequences

### Positive

- **Producción funcional** sin trabajo adicional inmediato.
- **Path absoluto inmune a quirks de shell**: no depende de `$PWD`, no se rompe si Render cambia el cwd en pre-build hooks, no requiere conocer si el shell es `bash` o `sh`.
- **Aprendizaje documentado.** Cualquier dev futuro que toque infra de Render ve este ADR antes de asumir que `render.yaml` es la fuente de verdad.
- **`/providers` queda como canario end-to-end de facto.** Si en el futuro un cambio rompe la instalación del extractor en prod, `/providers` lo va a delatar — no necesitamos infra de monitoreo adicional para esto.

### Negative

- **`render.yaml` NO es la fuente de verdad.** Drift potencial: alguien edita `render.yaml` pensando que afecta producción, el deploy no cambia, y se diagnostica como bug del código en vez de bug de configuración.
- **Cambios al `buildCommand` requieren editar la UI de Render**, no quedan en git, no se revisan en PR, no se trazan en commits. Para un repo con audit trail regulatorio en horizonte (STRATEGY § 13), esto es deuda real.
- **Si la cuenta de Render rota** (founder cambia, se migra a otra org, se transfiere el workspace), hay que recordar reconfigurar la UI desde cero porque el valor no vive en el repo. Mitigación: mantener `render.yaml` actualizado y documentar el comando exacto en `apps/api/RENDER.md`.
- **Bypass involuntario de revisión.** En el modelo de PR-revisado-luego-merge-luego-deploy-auto, infra cambia sin pasar por revisión. Aceptable en equipo de 1, riesgoso a partir de 3+ contributors.

### Neutral

- Render no documenta la precedencia UI > yaml en una sola página obvia. Está dispersa en la sección de Blueprints. Cualquier servicio nuevo en este workspace **debería crearse vía Blueprint puro** (sin UI override) o **vaciar explícitamente los campos** después del primer setup. Documentado en el plan de remediación.

## Plan de remediación

Sesión futura controlada (~30 min, no urgente, schedulear cuando `/extract` esté sin tráfico real):

1. **Pre-checks (5 min).**
   - Verificar que `HEAD` de `main` tiene `render.yaml` con `buildCommand` correcto (path absoluto + sanity check + install de `sica-api`).
   - Levantar `apps/api` localmente con `uvicorn` y verificar `/health`, `/providers`, `/models` responden bien con el extractor instalado.
   - Bajar el screenshot del `buildCommand` actual de la UI de Render para tener rollback rápido.

2. **Aplicación del fix (5 min).**
   - En la UI de Render → service `sica-api` → Settings → Build Command → **vaciar el campo** (string vacío, no whitespace).
   - Settings → Save.
   - Trigger **Manual Deploy** con "Clear build cache & deploy" para forzar build sin layers cacheados.

3. **Verificación post-deploy (10 min).**
   - `curl https://sica-api-d1gq.onrender.com/health` → `extractor_available: true`.
   - `curl https://sica-api-d1gq.onrender.com/providers | jq` → 2 providers, anthropic disponible.
   - `curl https://sica-api-d1gq.onrender.com/models` → 9 items, primeros con `is_available: true`.
   - **Si todo OK:** confirmar que se está ejecutando el `buildCommand` de `render.yaml` (debería poder verse en los build logs de Render).
   - **Si algo falla:** restaurar el valor del campo en UI usando el screenshot del paso 1. Producción vuelve a estado pre-remediación en <2 min.

4. **Cierre (10 min).**
   - Si éxito: editar este ADR agregando una sección **Migration log** con fecha de remediación y commit hash que verificó el comportamiento.
   - Si éxito: eliminar el comentario en `render.yaml` que advierte sobre la precedencia UI.
   - Si fallido: documentar qué falló y postergar.

**Trigger explícito para correr la remediación:**

- Llega un segundo contributor con permisos de Render → primero remediar para que todo cambio pase por PR.
- Hay un service más en Render (futuro `sica-eval` o `sica-orchestrator`) → mejor unificar todos vía Blueprint antes de que la deuda se multiplique.
- Auditoría de compliance Ley 29733 / DPIA pide trazabilidad de configuración de infra → forzado.

## Lecciones aprendidas

1. **`/providers` fue accidentalmente el mejor health-check end-to-end** que el API tenía. Endpoints que dependen ricamente del estado runtime exponen bugs de infra que health-checks superficiales esconden. Diseñar endpoints diagnósticos que se rompan ruidosamente cuando el entorno está mal **es un patrón válido** — no solo defensa contra usuarios, sino contra deploys silenciosamente rotos.

2. **La precedencia UI > yaml en Render NO está documentada de forma obvia.** Para nuevos servicios en este workspace (o cualquiera basado en Render con Blueprints), **regla operativa**: después del primer deploy, vaciar los campos Build Command / Start Command de la UI para forzar el uso de `render.yaml`. Documentar en `RENDER.md` de cada servicio.

3. **Múltiples `--amend` + `--force-push` no resuelven nada si el bug está en infraestructura, no en código.** Tres iteraciones del `buildCommand` no cambiaron el comportamiento de prod porque el `buildCommand` real estaba en otro lado. **Heurística:** si un cambio que debería tener efecto no lo tiene tras 2 redeploys completos con tiempo suficiente, **el problema NO está en el código que estoy editando** — buscar afuera (UI de servicio, secrets, env vars, build cache, DNS, CDN).

4. **Smoke tests end-to-end contra producción importan.** En 3 días desde el primer deploy, nunca se había hecho un smoke contra `/extract` real ni inspeccionado `/models` en producción. `extractor_available: true` en `/health` se había tomado como suficiente. **Regla nueva:** después de cada deploy nuevo de cualquier servicio, smoke contra **al menos un endpoint que toque el camino crítico** (no solo liveness).

5. **Health checks deben ser honestos por diseño, no por accidente.** El `/health` original solo verificaba la env var, lo que constituía una **mentira silenciosa** cuando el módulo no estaba instalado. El fix `extractor_available = settings.extractor_available AND extractor_module_available()` materializa que `extractor_available` significa "el endpoint `/extract` va a funcionar", no "tengo configurada la credencial".

## References

- **Commit del fix funcional:** `1483dc6` — `fix(api): install clinical_extractor in Render + harden /health check (production bug)`. Trae `extractor_status.py`, lógica AND en `/health`, tests del nuevo comportamiento, y `render.yaml` con `buildCommand` correcto (aunque ignorado por la UI).
- **Commit del canario:** `9606b8d` — `feat(api): add GET /providers endpoint with rich provider+model shape (closes Bloque E TODO)`. Endpoint que descubrió accidentalmente la deuda.
- **Issue relacionado:** sin issue formal — incidente detectado en sesión interactiva. Si necesita tracking explícito, crear issue "Vaciar buildCommand de Render UI y validar uso de render.yaml" con label `infra` apuntando a la sección Plan de remediación.
- **Documentación externa relevante:** [Render Blueprint Spec](https://render.com/docs/blueprint-spec), [Render Build Command settings](https://render.com/docs/configure-environment#environment-overrides).
- **Documentos internos:** `apps/api/RENDER.md` (checklist de setup manual), `render.yaml` (declaración aspiracional), STRATEGY § 13 (audit trail regulatorio).

## Revisión

Esta decisión se revisa explícitamente en uno de estos triggers:

- Se ejecuta el plan de remediación con éxito → este ADR queda **superseded by self** con sección Migration log.
- Se agrega un segundo servicio a Render → forzar revisión antes de heredar la deuda.
- Render cambia su modelo de precedencia (improbable pero posible) → reescribir el ADR.

Hasta entonces, **UI de Render es la fuente de verdad operacional** y `render.yaml` es snapshot referencial mantenido sincronizado a mano.
