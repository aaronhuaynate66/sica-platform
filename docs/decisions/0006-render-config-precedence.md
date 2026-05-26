# 0006. Render Dashboard UI tiene precedencia sobre `render.yaml`

- **Status:** Accepted — 2026-05-25 (actualizado 2026-05-26: validación empírica del plan de remediación; ver § Plan de remediación intentado y descartado)
- **Date:** 2026-05-25
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** infra, deploy, render, restriccion-plataforma, postmortem
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

### Actualización 2026-05-26 — la decisión es permanente, no temporal

Al intentar ejecutar el Plan de remediación documentado más abajo, se descubrió que **Render no permite guardar el campo Build Command vacío**. La UI rechaza la operación con error literal `Cannot be blank` al hacer Save Changes. Probado en el plan free, sobre el servicio creado vía UI (no vía Blueprint puro).

Esto cambia la naturaleza de esta decisión:

- **Ya no es deuda técnica con plan de remediación.** El `buildCommand` de UI **es la fuente de verdad definitiva** para Render — no por elección operativa nuestra sino por **restricción de la plataforma**.
- `render.yaml` queda como **espejo sincronizado a mano** para audit trail y rollback (si se rota la cuenta de Render hay que reconstruir el servicio y este yaml es la documentación canónica del comando que debe ir en la UI).
- El resto de campos de `render.yaml` (`startCommand`, `envVars`, `pythonVersion`, `healthCheckPath`, `autoDeploy`, etc.) **sí los lee y respeta Render** — la restricción aplica únicamente al campo Build Command. Ver § Implicaciones operativas.

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

## Plan de remediación intentado y descartado

> Esta sección reemplaza al Plan de remediación original (versión 2026-05-25) tras la validación empírica del 2026-05-26.

**Fecha del intento:** 2026-05-26.

**Pasos ejecutados:**

1. **Sincronización previa del yaml.** Commit `d74df95` — `chore(infra): sync render.yaml buildCommand with what production actually runs (ADR-0006 prep)`. Reemplazó el bloque multilínea con `set -e` por el one-liner con path absoluto, idéntico al string que ejecuta la UI de Render. Objetivo: que el switchover sea no-op.

2. **Intento de vaciar el campo en UI.** Dashboard de Render → service `sica-api` → Settings → Build Command → borrar todo el contenido del input → Save Changes.

3. **Resultado.** Render rechazó la operación con error literal:

   > **Cannot be blank**

   No es validación cliente-side bypasseable: el endpoint del backend de Render devuelve el error y el campo no se persiste. Probado en plan **free** sobre el servicio `sica-api` creado vía UI (no vía Blueprint puro).

**Conclusión.** La restricción es **de la plataforma**, no del setup del servicio. El campo Build Command es **required no-nullable** en la UI de Render para servicios web. Vaciarlo para forzar uso de `render.yaml` no es una operación que la plataforma permita.

**Implicaciones para la decisión original:**

- ❌ "Plan de remediación" como path al estado ideal **ya no existe**.
- ✅ La UI de Render queda como **fuente de verdad de jure y de facto** para el `buildCommand`.
- ⚠️ Cambios futuros al `buildCommand` ahora deben aplicarse **siempre en ambos lugares** (UI + yaml), tratando el yaml como espejo documentado.

**Caminos alternativos no descartados** (queda registro para sesiones futuras si la deuda se vuelve crítica):

- **Blueprint deployment puro.** Recrear el servicio desde cero declarándolo vía Blueprint (sin `Create Web Service` desde UI). En servicios creados así, los campos de UI pueden venir vacíos por default y `render.yaml` es autoritativo. Costo: migración del servicio existente con downtime, nueva URL pública, reconfigurar `ALLOWED_ORIGINS` en frontend, posiblemente reconfigurar secrets. No aplica en R0/R1 — sólo justificable cuando lleguemos a 3+ servicios en Render o cuando audit trail regulatorio lo exija.
- **Plan paid + soporte de Render.** Plan paid puede tener overrides distintos; consultar a Render support si la restricción aplica también ahí. No prioritario.

## Implicaciones operativas

Con la restricción confirmada como permanente, queda explícito qué partes de `render.yaml` son autoritativas y qué partes son espejo:

### Qué Render SÍ lee y respeta de `render.yaml`

Para el servicio `sica-api`, los siguientes campos del yaml **funcionan como fuente de verdad** — editarlos en el repo y pushear a `main` con `autoDeploy: true` aplica el cambio en el siguiente deploy:

- `startCommand` — comando de arranque del web service (uvicorn).
- `envVars` — variables de entorno declarativas (incluyendo `sync: false` para secrets que se setean a mano en UI, como `ANTHROPIC_API_KEY`).
- `pythonVersion` — versión de Python del runtime.
- `healthCheckPath` — path para liveness check de Render.
- `autoDeploy` — flag de auto-deploy en push a `main`.
- `region`, `plan`, `rootDir`, `runtime` — config base del servicio.

### Qué Render IGNORA de `render.yaml`

- `buildCommand` — **siempre** toma el valor del campo en UI, que no puede estar vacío.

### Regla operativa: cambios al `buildCommand`

**Cualquier modificación futura al `buildCommand` debe aplicarse en AMBOS lugares para mantener sincronía documental:**

1. **UI de Render** (efecto real en producción):
   - Dashboard → service `sica-api` → Settings → Build Command → editar → Save Changes.
   - Trigger Manual Deploy con "Clear build cache & deploy" si el cambio toca dependencias del extractor.
   - Verificar `/health` y `/providers` post-deploy (`extractor_available: true`, `total_providers: 2`).

2. **`render.yaml` en el repo** (audit trail + documentación):
   - PR (o commit directo a `main` si trabajamos en modo autónomo) con el `buildCommand` actualizado y commit message que liste el cambio.
   - El yaml NO afecta producción por sí solo, pero **es la única fuente trazable en git** del comando que está corriendo en Render.

**Anti-patrón a evitar:** modificar SOLO el yaml asumiendo que `autoDeploy` lo aplicará. Eso fue exactamente el bug del 22-may→25-may de este ADR.

### Caso "rotación / migración de cuenta de Render"

Si por algún motivo se rota la cuenta de Render, se migra a otra org, o se recrea el servicio desde cero:

- El `buildCommand` en UI **se pierde** (no vive en el repo).
- `render.yaml` queda como **única documentación** del comando que debe ir en el nuevo servicio.
- Procedimiento documentado en `apps/api/RENDER.md` (runbook): crear servicio nuevo + copiar exactamente el `buildCommand` del yaml al campo UI + configurar secrets faltantes.

### Servicios futuros en Render

Cuando se agregue un segundo servicio (futuro `sica-eval`, `sica-orchestrator`, etc.):

- **Evaluar Blueprint deployment puro** como alternativa antes de crearlo vía UI. Si Blueprint resulta autoritativo para `buildCommand` ahí, vale la pena migrar `sica-api` también (downtime planificado).
- Si por simplicidad operativa se crea vía UI: aplicar la misma regla de "doble fuente sincronizada a mano" desde el día uno, y referenciar este ADR en el `RENDER.md` del nuevo servicio.

## Lecciones aprendidas

1. **`/providers` fue accidentalmente el mejor health-check end-to-end** que el API tenía. Endpoints que dependen ricamente del estado runtime exponen bugs de infra que health-checks superficiales esconden. Diseñar endpoints diagnósticos que se rompan ruidosamente cuando el entorno está mal **es un patrón válido** — no solo defensa contra usuarios, sino contra deploys silenciosamente rotos.

2. **La precedencia UI > yaml en Render NO está documentada de forma obvia.** Para nuevos servicios en este workspace (o cualquiera basado en Render con Blueprints), **regla operativa**: después del primer deploy, vaciar los campos Build Command / Start Command de la UI para forzar el uso de `render.yaml`. Documentar en `RENDER.md` de cada servicio.

3. **Múltiples `--amend` + `--force-push` no resuelven nada si el bug está en infraestructura, no en código.** Tres iteraciones del `buildCommand` no cambiaron el comportamiento de prod porque el `buildCommand` real estaba en otro lado. **Heurística:** si un cambio que debería tener efecto no lo tiene tras 2 redeploys completos con tiempo suficiente, **el problema NO está en el código que estoy editando** — buscar afuera (UI de servicio, secrets, env vars, build cache, DNS, CDN).

4. **Smoke tests end-to-end contra producción importan.** En 3 días desde el primer deploy, nunca se había hecho un smoke contra `/extract` real ni inspeccionado `/models` en producción. `extractor_available: true` en `/health` se había tomado como suficiente. **Regla nueva:** después de cada deploy nuevo de cualquier servicio, smoke contra **al menos un endpoint que toque el camino crítico** (no solo liveness).

5. **Health checks deben ser honestos por diseño, no por accidente.** El `/health` original solo verificaba la env var, lo que constituía una **mentira silenciosa** cuando el módulo no estaba instalado. El fix `extractor_available = settings.extractor_available AND extractor_module_available()` materializa que `extractor_available` significa "el endpoint `/extract` va a funcionar", no "tengo configurada la credencial".

6. **Render UI tiene precedencia DURA sobre `render.yaml` para el campo Build Command — no es una preferencia de orden, es una restricción que impide vaciar el campo.** Confirmado empíricamente el 2026-05-26: la UI devuelve `Cannot be blank` al intentar guardar el campo vacío. Esto significa que **no existe el path "yaml-autoritativo" para `buildCommand`** en servicios creados vía UI; la única ruta a yaml-autoritativo es Blueprint deployment puro (con migración del servicio). Para todos los demás campos (`startCommand`, `envVars`, `pythonVersion`, `healthCheckPath`, `autoDeploy`, etc.), el yaml SÍ es autoritativo. **Heurística:** asumir que "yaml > UI" es una preferencia configurable es un anti-patrón; la jerarquía la define cada plataforma y a veces es no-overridable.

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
