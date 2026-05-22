# `lib/analytics/`

Capa de analítica de SICA web. Gestiona consentimiento, masking de PHI,
carga condicional de GA4 + Microsoft Clarity, y emisión de eventos
tipados.

## Flujo de ejecución

```
Usuario abre la app
        │
        ▼
ConsentBanner aparece (consent === "pending")
        │
        ▼
Usuario hace click "Aceptar"     ──►   accept() → localStorage "granted"
        │                                     │
        │                                     ▼
        │                          <GoogleAnalytics/> + <MicrosoftClarity/>
        │                          detectan granted → cargan gtag.js + clarity.js
        │                                     │
        ▼                                     ▼
Componentes llaman trackEvent  ──►  gtag('event', ...) / clarity('event', ...)
        │
        ▼
sanitizeParams() filtra PHI antes de cada envío
```

Si el usuario rechaza o nunca decide: ningún script se carga, todos los
`trackEvent` son noop silencioso.

## Componentes de la capa

| Archivo | Rol |
|---|---|
| `use-consent.ts` | Hook con estado del consentimiento (`granted` \| `denied` \| `pending`), persiste en localStorage. |
| `use-analytics.ts` | Hook `trackEvent` / `trackPageView` con sanitizeParams. Noop si consent ≠ granted. |
| `masking.ts` | `applyMaskingProps()` aplica `data-clarity-mask=true` + `data-no-track=true`. Lista de elementos enmascarados. |
| `events.ts` | Catálogo `ANALYTICS_EVENTS` de nombres de eventos válidos. Fuente única de verdad. |
| `../../components/site/consent-banner.tsx` | Banner sticky que renderiza cuando consent === pending. |
| `../../components/analytics/google-analytics.tsx` | Carga gtag.js sólo si env var + consent. |
| `../../components/analytics/microsoft-clarity.tsx` | Carga clarity.js sólo si env var + consent. |
| `../../app/privacy/page.tsx` | Política de privacidad, link al estado actual + botón reset. |

## Agregar un evento nuevo

1. Agregar la constante en `events.ts`:

   ```ts
   export const ANALYTICS_EVENTS = {
     // …
     MI_EVENTO_NUEVO: "mi_evento_nuevo",
   } as const;
   ```

2. Documentar en el comment de la constante: qué dispara el evento + qué
   params lleva. Los params deben ser **primitivos cortos** (number,
   boolean, strings <100 chars).

3. En el componente que dispara el evento:

   ```tsx
   import { useAnalytics } from "@/lib/analytics/use-analytics";
   import { ANALYTICS_EVENTS } from "@/lib/analytics/events";

   const { trackEvent } = useAnalytics();
   trackEvent(ANALYTICS_EVENTS.MI_EVENTO_NUEVO, { duration_ms: 123 });
   ```

4. **Antes de commitear**, revisar mentalmente cada param:

   - ¿Es un texto que el usuario escribió o que vino del documento? → ❌
     dropea, no se trackea.
   - ¿Es un ID corto, un enum o una métrica numérica? → ✅ OK.

   `sanitizeParams()` te cubre si te equivocás (recorta strings >100 chars,
   descarta objects/arrays), pero la **defensa principal es no enviar PHI
   en primer lugar**.

## Verificar que funciona

1. Levantar la app local con vars vacías (default): los scripts no cargan.

2. Para probar la integración real, pegar en `.env.local`:

   ```
   NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
   NEXT_PUBLIC_CLARITY_PROJECT_ID=xxxxxxxxxx
   ```

   Reiniciar `pnpm dev`.

3. Abrir incognito en `http://localhost:3000`.

4. Ver el banner de consentimiento abajo, encima del disclaimer.

5. Click **Aceptar**.

6. DevTools → Network → filtrar `google-analytics` o `clarity`:

   - Debería aparecer un GET a `googletagmanager.com/gtag/js?id=…`.
   - Debería aparecer un GET a `clarity.ms/tag/<projectId>`.
   - Tras hacer cualquier acción, beacons `collect` (GA4) y `c.clarity.ms`
     (Clarity) llegan.

7. Recargar el incognito sin limpiar storage → el banner ya no aparece.

8. Ir a `/privacy` → click "Cambiar mi decisión" → el banner reaparece al
   volver a `/`.

## PHI masking

Atributos aplicados:

- `data-clarity-mask="true"`: Clarity reemplaza el contenido por un
  bloque opaco en las grabaciones de sesión.
- `data-no-track="true"`: convención interna, documenta intención.
  Útil para auditoría: `grep -r "data-no-track" apps/web/components`
  enumera todo lo sensible.

Elementos actualmente enmascarados:

| Componente / archivo | Qué se enmascara |
|---|---|
| `summary-view.tsx` | `<iframe>` del PDF + `<CardContent>` de Datos gestacionales, Problemas activos, Laboratorios y Resumen/plan. |
| `evidence-modal.tsx` | `<article>` de cada span + `<pre>` con texto verbatim del PDF. |
| `editable-field.tsx` | `<span>` de modo lectura + `<input>` / `<textarea>` de modo edición. |
| `edits-indicator.tsx` | `<dd>` de original y nuevo en el modal de diff. |

Si agregás un componente nuevo que muestre datos extraídos del PDF,
**aplicalo desde el primer commit**.

```tsx
import { applyMaskingProps } from "@/lib/analytics/masking";

<span {...applyMaskingProps()}>{patientAge}</span>
```

## Por qué hay sanitización de params

Defensa en profundidad. El flujo correcto es:

1. La capa de UI **no debería pasar PHI a `trackEvent`** en primer lugar.
2. Si lo pasa por error, `sanitizeParams` lo detecta heurísticamente
   (strings >100 chars, objects, arrays) y lo descarta antes de mandarlo a
   Google/Microsoft.
3. En dev mode emite `console.warn` para que el desarrollador note el
   problema en tiempo de desarrollo.

Whitelist de tipos permitidos en params:

- `number` (incluso `0`)
- `boolean` (incluso `false`)
- `string` con `length > 0 && length <= 100`

Todo lo demás se descarta silenciosamente en producción, con warning en
development.

## Limitaciones conocidas (R0)

- **No SPA page_view automático**: Next.js App Router no dispara
  `page_view` al cambiar de ruta. El evento `view_changed` lo
  reemplaza para los clicks de nav; navegaciones por URL directa no
  se trackean.
- **CONSENT_GRANTED puede perderse**: tras click Accept, hay un timeout
  de 150ms para que `gtag` cargue. Si la red es lenta, el evento se
  pierde. Es de baja prioridad — la siguiente acción del usuario sí se
  trackea normalmente.
- **CONSENT_DENIED no se envía**: por diseño — si rechazaron, no
  llamamos a Google. La decisión se persiste en localStorage para que
  el banner no reaparezca.
- **Sin User ID**: cada visita es anónima. Cuando exista auth, se puede
  enriquecer con `gtag('config', id, { user_id: ... })` desde el lado
  del cliente, respetando consent.
