# SICA

![Status](https://img.shields.io/badge/status-phase%201-blue)
![Stage](https://img.shields.io/badge/stage-pre%20product-orange)
![License](https://img.shields.io/badge/license-proprietary-red)

**Sistema de Inteligencia Clínica Asistida**

Clinical Intelligence Infrastructure para salud materno-infantil en mercados emergentes, empezando por Perú.

SICA es la primera capa cognitiva longitudinal que conecta el journey clínico materno-infantil completo — embarazo, parto, neonatología, pediatría — montada sobre los HIS y SIHCE existentes sin reemplazarlos. Es un copiloto clínico **asistivo**, no diagnóstico autónomo, con doctor-in-the-loop y explainability por diseño.

---

## Estado del proyecto

**Fase 1 — Consolidación estratégica.** Documentos estratégicos son fuente de verdad. Aún no hay código.

**Próximos hitos**

1. Validar `STRATEGY.md` con asesor clínico y asesor regulatorio.
2. Definir partner fundador (clínica privada materno-infantil en Lima).
3. Identificar 5 KOLs target para Distribution Engine.
4. Pasar a Fase 2 — construcción de monorepo y capa de ejecución.

---

## Estructura del repo

```
sica/
├── README.md                       ← este archivo
├── SECURITY.md                     ← política de divulgación responsable (GitHub Security)
├── STRATEGY.md                     ← documento estratégico, fuente de verdad (21 secciones)
├── STRATEGY.v0.1.backup.md         ← backup de versión anterior
├── MASTER_PLAN.md                  ← estado operativo auto-generado (no editar a mano)
├── docs/
│   ├── roadmap.md                  ← roadmap detallado R0–R5
│   ├── glossary.md                 ← glosario clínico, técnico, regulatorio
│   ├── fundraising-narrative.md    ← narrativa VC (BORRADOR — uso interno fundraising)
│   ├── operating-model.md          ← AI-native company operations (placeholder Fase 2)
│   ├── security/                   ← políticas de seguridad y compliance (PHI, Ley 29733, incident response, threat model)
│   └── decisions/                  ← ADRs
├── .gitignore
└── LICENSE                         ← pendiente: decidir licencia
```

---

## Documentos clave

| Documento | Para quién | Cuándo usar |
|---|---|---|
| `STRATEGY.md` | Founders + asesores clínicos/regulatorios + (eventualmente) inversores | Fuente de verdad estratégica |
| `MASTER_PLAN.md` | Cualquiera que entre al repo | Estado operativo en vivo: progreso por release, milestones, bloqueantes, ADRs, commits. **Auto-generado** — no editar a mano. Ver [ADR 0002](docs/decisions/0002-living-roadmap-system.md). |
| `SECURITY.md` | Cualquiera que encuentre una vulnerabilidad | Cómo reportarla de forma responsable. Para reportar vulnerabilidades, ver `SECURITY.md`. |
| `docs/security/` | Equipo + asesor regulatorio + auditor + partner | Políticas de seguridad y compliance: manejo de PHI, Ley 29733, incident response, threat model. Ver [ADR 0003](docs/decisions/0003-security-and-phi-policy.md). |
| `docs/roadmap.md` | Equipo de producto e ingeniería | Planificación operativa R0-R5 |
| `docs/fundraising-narrative.md` | **Solo founders + inversores** | Pitch a VC — NO compartir con asesores ni prospects clínicos |
| `docs/operating-model.md` | Equipo interno | Cómo operamos como AI-native company |
| `docs/glossary.md` | Cualquiera (especialmente nuevos miembros) | Referencia rápida de términos |

---

## Disclaimer

Este repositorio contiene material estratégico y de producto en fase pre-construcción. Nada de lo aquí descrito constituye:

- una afirmación regulatoria,
- un compromiso comercial,
- una validación clínica formal.

Todos los claims de producto se entienden como **hipótesis a validar**, no como capacidades probadas. La validación clínica formal, la inscripción de banco de datos personales ante la ANPD, y la consulta con DIGEMID son **pasos requeridos antes de exposición a paciente real**.

Las políticas de seguridad y manejo de PHI están documentadas en [`SECURITY.md`](SECURITY.md) y [`docs/security/`](docs/security/) — su revisión y firma por asesor regulatorio externo es bloqueante para procesar el primer dato real. Ver lista completa de bloqueantes en [`docs/security/ley-29733-compliance.md`](docs/security/ley-29733-compliance.md).

---

## Deployment

| Componente | Plataforma | Estado | Documentación |
|---|---|---|---|
| `apps/web` | Vercel (frontend Next.js) | Pendiente primer deploy manual | [`apps/web/VERCEL.md`](apps/web/VERCEL.md) — checklist exacto para configurar el proyecto en la UI de Vercel |
| `apps/api` | Cloud Run (backend Python FastAPI) | TODO | Ver issue R0 — Dockerfile + deploy script pendientes |
| `services/clinical-extractor` | N/A (librería consumida por `apps/api`) | Local-only | — |

El cliente HTTP de `apps/web` (`lib/api/client.ts`) opera en dos modos según `NEXT_PUBLIC_API_MODE`:

- `demo` (default Vercel actual) — usa fixture sintético, sin red.
- `live` — invoca `apps/api` real con fallback automático a demo si `/health` falla.

CORS de `apps/api` permite por default `https://*.vercel.app` (preview deploys). Refinar `ALLOWED_ORIGIN_REGEX` cuando exista dominio de producción.

## Contacto

Owner: ver perfil de GitHub del repo. Equipo y roles fundadores en `STRATEGY.md` § 19.
