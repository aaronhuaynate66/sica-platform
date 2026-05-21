# SICA

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
├── STRATEGY.md                     ← documento estratégico, fuente de verdad (21 secciones)
├── STRATEGY.v0.1.backup.md         ← backup de versión anterior
├── docs/
│   ├── roadmap.md                  ← roadmap detallado R0–R5
│   ├── glossary.md                 ← glosario clínico, técnico, regulatorio
│   ├── fundraising-narrative.md    ← narrativa VC (BORRADOR — uso interno fundraising)
│   ├── operating-model.md          ← AI-native company operations (placeholder Fase 2)
│   └── decisions/                  ← ADRs (pendiente Fase 2)
├── .gitignore
└── LICENSE                         ← pendiente: decidir licencia
```

---

## Documentos clave

| Documento | Para quién | Cuándo usar |
|---|---|---|
| `STRATEGY.md` | Founders + asesores clínicos/regulatorios + (eventualmente) inversores | Fuente de verdad estratégica |
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

---

## Contacto

Owner: ver perfil de GitHub del repo. Equipo y roles fundadores en `STRATEGY.md` § 19.
