# STRATEGY.md — SICA

**Sistema de Inteligencia Clínica Asistida**
**Versión 0.1 — Fase 1 (Consolidación estratégica)**
**Última actualización:** 2026-05-20

---

## Cómo leer este documento

Este es el documento estratégico fundacional de SICA. Sirve tres audiencias:

1. **Founders y equipo interno** — para alinear decisiones de producto, ingeniería y comercial.
2. **Asesores externos** (clínico, regulatorio, legal) — para que validen supuestos críticos antes de construir.
3. **Inversores potenciales** (más adelante, no ahora) — como base de pitch deck y narrativa.

**Convención:**
- `[TODO]` señala trabajo pendiente que NO debe inventarse — requiere investigación real, entrevistas o validación externa.
- `[ASUMIDO]` señala supuesto de trabajo que ordena el plan pero debe validarse con dato local.
- `[CITADO]` señala dato anclado en fuente verificable (ENDES, MINSA, etc.).

**Status del documento:** borrador interno. No compartir fuera del equipo hasta versión 1.0.

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Tesis y posicionamiento](#2-tesis-y-posicionamiento)
3. [Problema y validación de mercado](#3-problema-y-validación-de-mercado)
4. [Producto: visión y casos de uso](#4-producto-visión-y-casos-de-uso)
5. [Roadmap de producto R0–R5](#5-roadmap-de-producto-r0r5)
6. [Arquitectura técnica](#6-arquitectura-técnica)
7. [Validación clínica](#7-validación-clínica)
8. [Marco regulatorio peruano](#8-marco-regulatorio-peruano)
9. [Go-to-market](#9-go-to-market)
10. [Modelo de negocio y proyecciones](#10-modelo-de-negocio-y-proyecciones)
11. [Riesgos y mitigación](#11-riesgos-y-mitigación)
12. [Equipo y hiring](#12-equipo-y-hiring)
13. [Lo que NO entra en Fase 1](#13-lo-que-no-entra-en-fase-1)
14. [Pendientes críticos (TODOs)](#14-pendientes-críticos-todos)

---

## 1. Resumen ejecutivo

**SICA es un copiloto clínico asistivo para salud materno-infantil**, vendido B2B a clínicas privadas medianas en Perú con servicios de obstetricia, neonatología y centro quirúrgico.

**Tesis central.** Existe una ventana de mercado en Perú donde coexisten (a) una carga clínica relevante en salud materno-neonatal y (b) una digitalización aún incompleta con interoperabilidad recién en consolidación. La oportunidad no es construir un nuevo HIS, sino una **capa de inteligencia clínica que se monta sobre lo que ya existe** y reduce fricción cognitiva en momentos críticos.

**Wedge inicial.** Resumen longitudinal obstétrico + handoff materno-neonatal. Dos workflows, una clínica fundadora, 18 meses para llegar a sede 2 firmada.

**Por qué SICA y no otro:**

1. **Posicionamiento "asistido" como ventaja regulatoria.** El claim está construido en el branding. No diagnostica, no decide, no es autónomo. Esto mantiene a SICA fuera de la órbita de dispositivo médico DIGEMID en Fase 1, reduciendo fricción regulatoria.
2. **Arquitectura multimodal interoperable desde día uno.** FHIR R4 como backbone canónico, MedGemma local como default para PHI, Gemini como escalamiento puntual, MedSigLIP para retrieval visual. No es lock-in con un solo proveedor.
3. **Doctor-in-the-loop por diseño, no por marketing.** Cada output muestra evidencia trazable, timestamp, nivel de confianza. El médico edita o rechaza. Auditoría completa.
4. **B2B antes de B2C.** El primer presupuesto a capturar es clínico-operacional, no de consumo. El B2C (companion materno) puede llegar como extensión, no como entrada.

**Métricas de éxito a 18 meses:**
- 1 partner fundador con SICA en producción shadow + asistivo en obstetricia, neonatología y anestesia.
- Sede 2 firmada con plan Materno-Neo Core.
- Benchmark clínico documentado: >95% exactitud factual en resumen obstétrico, >95% completitud en handoff materno-neonatal.
- Renovación anual del partner fundador.

**Capital requerido para 18 meses:** USD 213,000 brutos, potencialmente USD 120,000–140,000 netos si se materializan dos pilotos pagados desde el mes 6–8 y créditos cloud. `[ASUMIDO — modelo del deep research, sin validación de mercado]`

---

## 2. Tesis y posicionamiento

### 2.1 Qué es SICA

SICA es:

- una **infraestructura de inteligencia clínica longitudinal**,
- especializada en **ginecología, obstetricia, neonatología, pediatría y anestesiología**,
- vendida como **SaaS B2B clínico** a clínicas privadas medianas,
- diseñada para **convivir con HIS/SIHCE existentes**, no reemplazarlos,
- con **modelos de IA orquestados**: MedGemma local, MedSigLIP, Gemini cloud, según tarea y sensibilidad de datos.

### 2.2 Qué SICA NO es

| No es | Por qué importa la distinción |
|---|---|
| Un sistema de diagnóstico autónomo | Cambia clasificación regulatoria a dispositivo médico DIGEMID, dispara validación clínica formal larga y costosa |
| Un chatbot médico para pacientes | Mercado distinto, riesgo regulatorio distinto, no es B2B clínico |
| Una app de embarazo / pregnancy tracker | El comprador es la madre, no la clínica. Modelo de negocio distinto |
| Un HIS / EHR de reemplazo | Ciclo de venta de 18+ meses, costo de implementación 10x, no es bootstrap-able |
| Una plataforma de telemedicina | Norma Técnica de Telesalud 2025 añade superficie regulatoria; clínicas materno-infantiles privadas peruanas reportan no ofrecer virtual `[CITADO — clínica de referencia segmento, deep research §1]` |
| Un CRM o automatización administrativa | Mercado distinto, valor distinto, no captura el wedge clínico |

### 2.3 Filosofía de producto

Cuatro principios no negociables:

1. **Doctor-in-the-loop.** Ningún output llega a flujo crítico sin confirmación médica explícita.
2. **Explainability-first.** Cada hecho viene con fuente, timestamp y confianza. Si no hay evidencia, el sistema dice "no encontrado" — no rellena.
3. **Regulatory-aware.** Cada feature pasa filtro regulatorio antes de pasar filtro de utilidad.
4. **Clinically grounded.** Las métricas de éxito las define el médico, no el growth team. Tasa de aceptación, tiempo ahorrado real, brechas detectadas correctamente.

### 2.4 Comparables y posicionamiento competitivo

| Comparable | Vertical | Mercado primario | Diferencial de SICA |
|---|---|---|---|
| **Abridge** | Ambient scribe general | US enterprise | SICA es materno-infantil específico, no scribe genérico |
| **Nabla** | Ambient scribe general | US, EU | Igual que Abridge |
| **Suki** | Voice assistant clínico | US | SICA es razonamiento + memoria, no solo voz |
| **Ambience Healthcare** | Ambient + summarization | US | Más general; SICA es vertical materno-infantil |
| **Hippocratic AI** | LLM clínico de propósito amplio | US enterprise | Diferente modelo de operación; SICA es capa, no agente conversacional |
| **Glass Health** | Reasoning para diagnóstico | US, B2C/B2B | Más cerca a diagnóstico; SICA mantiene posición asistiva |
| **OpenEvidence** | Knowledge retrieval médico | US clínicos | SICA integra workflow + memoria longitudinal, no solo evidence retrieval |
| **Epic / Athenahealth** | HIS completo | US, global | SICA no compite, se integra |
| **Google MedGemma / MedSigLIP / Gemini Health** | Modelos base | Global | SICA los usa, no compite con ellos |

**Análisis competitivo en Perú/LatAm:** `[TODO crítico]` — investigación de campo pendiente. Hipótesis a validar: en Perú no existe hoy un competidor con tesis equivalente (copiloto clínico vertical materno-infantil con FHIR + multi-modelo). Hay players adyacentes (HIS locales, integradores, soluciones de telemedicina) pero no en el wedge. **Validar antes de pitch a inversores.**

---

## 3. Problema y validación de mercado

### 3.1 Carga clínica que justifica el producto

En Perú, la salud materno-infantil sigue siendo prioridad pública. Indicadores relevantes `[CITADO — MINSA / ENDES, deep research §1-2]`:

- **Razón de mortalidad materna 2023 (MINSA preliminar):** 51.9 por 100,000 nacidos vivos.
- **Mortalidad neonatal 2024:** 9 por 1,000 nacidos vivos.
- **Prematuridad:** subió de 6.9% (2022) a 7.7% (2024).
- **Causas principales identificadas por MINSA:** prematuridad, malformaciones congénitas, asfixia, infecciones.
- **Control prenatal ENDES 2023:** 98.1% de gestantes accedieron a controles.
- **Cobertura ≥6 controles 2024:** 87.86%.
- **Cumplimiento meta física "gestante controlada":** 63.5%.
- **Anemia 6–35 meses 2024:** 43.7% medición tradicional / 35.3% nueva directriz OMS 2024.
- **Cesárea nacional:** 37.8%. **Lima Metropolitana:** 49.0%.

**Lectura estratégica.** Hay acceso amplio a control prenatal, pero **no continuidad, completitud ni trazabilidad** en el journey completo. Eso es exactamente lo que SICA ataca.

### 3.2 Timing regulatorio

- **Ley 30024 — RENHICE.** Reglamento actualizado 2025. `[CITADO — deep research §1]`
- **Directiva de acreditación SIHCE.** Aprobada marzo 2025, plazos ampliados 2026.
- **Primera Conectatón nacional de interoperabilidad de HCE:** junio 2025.

**Lectura estratégica.** El ecosistema peruano está en transición activa hacia interoperabilidad real, pero **el estándar aún no está maduro**. Esto abre ventana para un integrador clínico útil **antes** de que la capa estándar se consolide. Si SICA llega tarde (post-2028), compite contra un mercado más maduro y menos abierto.

### 3.3 Usuarios objetivo

| Rol | Workflow | Job-to-be-done | Fricción actual |
|---|---|---|---|
| Obstetra | Consulta, guardia, centro obstétrico | Entender embarazo actual + riesgos + labs pendientes + plan de parto | Reconstruir línea de tiempo desde notas dispersas y PDFs |
| Ginecólogo | Consulta, quirófano | Antecedentes, resultados clave, indicación operatoria | Historia longitudinal incompleta entre consultas |
| Pediatra / CRED | Consulta pediátrica, seguimiento | Detectar brechas CRED, anemia, vacunas, desarrollo | Revisión seriada manual de controles |
| Neonatólogo | Sala de partos, UCIN, alojamiento conjunto | Recibir contexto materno + tamizajes + vacunas + riesgos | Handoff incompleto entre obstetricia y neonatología |
| Anestesiólogo obstétrico | Centro quirúrgico, cesáreas, urgencias | Brief preanestésico confiable en minutos | Datos críticos repartidos en historia, labs, notas |
| Director médico / Calidad | Gerencia clínica | Reducir tiempo improductivo + errores de handoff + no conformidades | ROI difícil sin integración al workflow |
| TI / transformación digital | Backoffice | Integrar sin romper SIHCE y sin elevar riesgo regulatorio | Interoperabilidad parcial, baja estandarización |

**Comprador inicial (decisión de compra):** Director médico + jefe de obstetricia/neonatología, con visto bueno de TI. **No es el médico individual.**

---

## 4. Producto: visión y casos de uso

### 4.1 Capacidades core del sistema

SICA se construye sobre **cinco capacidades** que interactúan:

1. **Clinical Memory Graph** — memoria clínica longitudinal que conecta antecedentes, evolución, síntomas, labs, ecografías, procedimientos, riesgos, timelines gestacional y neonatal, crecimiento pediátrico, evolución anestésica, outcomes. Implementada con knowledge graph + vector memory + embeddings médicos + temporal reasoning.

2. **Clinical Reasoning Engine** — motor que detecta patrones, correlaciona datos, sugiere hipótesis diferenciales, detecta riesgos longitudinales, encuentra inconsistencias, prioriza señales. **NO diagnostica. Decision support, no decision making.**

3. **Multimodal Ingestion Layer** — extracción estructurada desde PDFs, ecografías, reportes escaneados, HL7v2, FHIR parcial, CSV. OCR médico + parsers + extracción.

4. **Explainability Layer** — cada output médico incluye razonamiento, evidencia, variables relevantes, correlaciones detectadas, referencias clínicas, guideline relacionada, confidence scoring.

5. **Physician Copilot UI** — UX optimizada para minimizar carga cognitiva. Embed en HIS (launch button contextual), respuesta <2 segundos en pre-consulta, output siempre editable, evidencia visible. Inspiración: Linear, Notion, Bloomberg Terminal, Palantir Gotham.

### 4.2 Casos de uso priorizados (MVP)

| Prioridad | Caso de uso | Qué produce | Especialidades |
|---|---|---|---|
| Muy alta | Resumen clínico longitudinal | Resumen editable con evidencia, línea de tiempo, problemas activos | Ginecología, obstetricia, pediatría, neonatología |
| Muy alta | Copiloto documental | Extrae estructura de labs, reportes, ecografías, PDFs, notas escaneadas | Todas |
| Muy alta | Checklist y care gaps | Señala vacíos relevantes por guideline local o protocolo interno | Obstetricia, pediatría, neonatología |
| Alta | Brief preanestésico obstétrico | Resumen de cesárea / cirugía con datos críticos y riesgos | Anestesiología, obstetricia |
| Alta | Handoff materno-neonatal | Pasa contexto materno relevante a recepción neonatal / UCIN | Neonatología, obstetricia |

### 4.3 Lo que sigue después del MVP

| Fase | Feature | Por qué después |
|---|---|---|
| Siguiente | Dictado / ambient scribe médico | Reduce más carga documental sin entrar a diagnóstico |
| Siguiente | Analytics de calidad y cumplimiento | Vende a dirección médica, no solo al usuario final |
| Posterior | Clasificación / retrieval multimodal de imágenes | Requiere dataset local validado |
| Posterior | Companion B2C para madre y familia | Extensión natural del B2B, no entrada inicial |

---

## 5. Roadmap de producto R0–R5

Resumen del roadmap a 18 meses. Detalle completo y métricas de salida por release en [`docs/roadmap.md`](docs/roadmap.md).

**Principios del roadmap:**

1. Cada release pasa un **gate clínico/técnico** antes de pasar al siguiente. No avanzamos a un nuevo caso de uso si el anterior no cumplió métrica.
2. El primer release **no es un feature, es un benchmark**. Si MedGemma no alcanza umbral en historias locales, el stack de modelos se reconsidera **antes** de construir UI clínica.
3. **Shadow mode es la barrera natural entre alpha y beta.** Nada se muestra al médico en flujo real hasta que pasó shadow. Nada es mandatorio hasta que pasó piloto asistivo medido.

| Release | Mes | Wedge | Gate clave de salida |
|---|---|---|---|
| **R0 Foundation** | 0–2 | Benchmark + stack mínimo, sin UI clínica | MedGemma 4B ≥85% exactitud factual, ≤5% omisiones críticas en resumen obstétrico |
| **R1 Resumen Obstétrico (Alpha)** | 2–5 | Resumen longitudinal en panel standalone, uso en sesiones de revisión | >70% resúmenes calificados útiles sin edición mayor por ≥5 obstetras |
| **R2 Shadow + Checklist Prenatal** | 5–8 | Embed en HIS, generación automática pre-consulta, no mandatorio | ≥40% uso en consultas obstétricas + recall brechas ≥80% + 0 incidentes de seguridad |
| **R3 Handoff Materno-Neonatal (Asistivo)** | 8–11 | Primer flujo crítico: contexto materno disponible en recepción neonatal | Completitud ≥95% en 30 handoffs consecutivos + correcciones críticas <10% + aprobación jefatura neonatología |
| **R4 Brief Preanestésico Obstétrico** | 11–14 | Brief generado al programar cesárea o ante emergencia | <10% correcciones críticas en 50 briefs + aprobación jefe anestesiología + comité de calidad |
| **R5 Pediatría/CRED + Multi-sede** | 14–18 | Continuidad madre→bebé, módulo CRED, playbook de onboarding | Sede 2 onboarded antes mes 18 + renovación partner fundador en plan core |

### 5.1 Decisiones explícitas dentro del roadmap

- **R3 (handoff neonatal) antes que R4 (brief anestésico).** Razón: menor riesgo legal (handoff pasa información, brief preanestésico toca decisión farmacológica), y ROI más visible para dirección médica. `[Revisable si el partner fundador tiene volumen de cesárea programada significativamente mayor a volumen de UCIN]`.
- **R0 de 2 meses asume que el partner ya firmó acceso a datos.** Si no, R0 se extiende a 3 meses y todo el roadmap se desplaza.
- **CRED al final, no antes.** Razón: depende de continuidad longitudinal (meses de seguimiento del mismo bebé). Construirlo antes de R3 sería un feature huérfano sin datos para ejercitar.

### 5.2 Lo que deliberadamente NO entra en estos 18 meses

| Feature | Razón |
|---|---|
| Ambient scribe / dictado | Superficie regulatoria de datos en tiempo real; Mes 18+ |
| Triage de imagen con MedSigLIP | Requiere dataset local validado; primero corpus narrativo |
| Companion B2C | Mata el foco; extensión de R5+ |
| Telemedicina / teleconsulta | Norma Técnica de Telesalud añade fricción regulatoria |
| Diagnóstico autónomo | Cambia clasificación regulatoria — no en este horizonte |
| Expansión Chile / Colombia | Si llega, post-mes 18 con caso instalado en Perú |

---

## 6. Arquitectura técnica

### 6.1 Principios arquitectónicos

1. **El modelo de datos canónico es la pieza central, no el LLM.** FHIR R4 como representación canónica de todo lo clínico.
2. **Multi-modelo con routing explícito.** No depender de un solo proveedor de IA. MedGemma local default; Gemini para escalamiento puntual; MedSigLIP para retrieval visual.
3. **PHI sensible nunca sale a cloud sin política explícita.** Default es procesamiento local; escalamiento cloud es decisión deliberada por workflow.
4. **Cada output queda auditado.** Versión de modelo + prompt + datos de entrada + timestamp + edición/aceptación del médico. Esto es el corazón del audit trail clínico y regulatorio.
5. **Embebible, no reemplazante.** UI vive como launch button contextual desde el HIS del partner, no como nuevo HIS.

### 6.2 Diagrama de flujo (alto nivel)

```
HIS / SIHCE / LIS / PACS / PDFs / Imágenes / CNV
                    ↓
        Conectores: HL7v2 / FHIR / CSV / SFTP / API
                    ↓
            Normalización clínica
                    ↓
      ┌─────────────────────────────────┐
      ↓                                 ↓
  FHIR Store canónico            Object Storage
                                  (documentos)
                                       ↓
                                  OCR / parsing
                                       ↓
                                  → FHIR Store
                    ↓
      Índices RAG + búsqueda híbrida (pgvector / FAISS)
                    ↓
            Orquestador clínico
            ┌──────┼──────┬──────┐
            ↓      ↓      ↓      ↓
        Reglas  MedGemma MedSigLIP Gemini
        protocolos
                    ↓
        Panel web embebible en EHR
                    ↓
        Médico: confirma / edita / rechaza
                    ↓
        Auditoría + feedback + mejora continua
```

### 6.3 Stack

| Capa | Tecnología recomendada | Alternativa on-prem / híbrida |
|---|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind + shadcn/ui | Igual |
| Modelo clínico canónico | FHIR R4 (Patient, Encounter, Observation, Condition, DiagnosticReport, Procedure, CarePlan, Appointment, Practitioner) | HAPI FHIR autogestionado |
| Backend transaccional | Supabase / PostgreSQL | PostgreSQL self-hosted |
| Vector store | pgvector para arranque; FAISS si crece volumen | pgvector + FAISS local |
| Object storage | GCS / S3 con versionado | MinIO con cifrado |
| OCR / parsing | Document AI (escaneados); Gemini (PDFs nativos) | OCR local + parser propio |
| Orquestación LLM | FastAPI + LangGraph + motor de políticas + caché | Igual |
| Modelos | MedGemma 4B local (default PHI); MedSigLIP (retrieval visual); Gemini 2.5 Flash (escalamiento) | MedGemma 27B text-only si hardware lo permite |
| Infra | Cloud Run + GCP + Cloudflare; Docker; Kubernetes para crecimiento | On-prem + Docker para clínicas con requisitos estrictos |
| Observabilidad | OpenTelemetry + Langfuse + Sentry + Grafana | Igual |
| Analytics producto | PostHog (self-hosted opcional) | Igual |
| MLOps | LangGraph + DSPy + evaluation pipelines + prompt versioning | Igual |
| Security | RBAC, audit logs, encryption at rest/transit, tenant isolation, zero-trust en producción | Igual |

### 6.4 Política de routing de modelos

| Tarea | Modelo default | Fallback / escalamiento | Razón |
|---|---|---|---|
| Resumen de notas, labs, reportes | MedGemma 4B local | Gemini 2.5 Flash si contexto >32k tokens | PHI sensible, latencia importa |
| Extracción estructurada de PDF nativo | Gemini 2.5 Flash | MedGemma 4B local | Gemini tiene visión nativa de PDFs |
| OCR de PDF escaneado | Document AI | Tesseract local | Document AI optimizado para manuscritos |
| Retrieval / búsqueda visual | MedSigLIP embeddings | — | Encoder dedicado, no generación |
| Razonamiento clínico complejo (handoff con contexto largo) | MedGemma 27B text-only si disponible; Gemini 2.5 Pro si no | — | Profundidad >tarea simple |
| Care gaps / detección de brechas | Reglas + retrieval híbrido + MedGemma 4B | — | Tarea estructurada, no narrativa |
| Cualquier output con baja confianza | **Abstención obligatoria** | El médico decide sin sugerencia | "No encontrado" > "alucinado" |

### 6.5 Costos de cómputo (anclajes técnicos)

`[CITADO — Google Cloud pricing, deep research §6]`

| Opción | Tarifa oficial | Costo aprox. mensual 24/7 | Uso recomendado |
|---|---:|---:|---|
| G2 `g2-standard-4` (1× L4) | USD 0.7068/h | USD 516/mes | Inferencia liviana, embeddings, MVP controlado |
| A2 `a2-highgpu-1g` (1× A100) | USD 3.6734/h | USD 2,682/mes | Inferencia robusta, concurrencia media |
| A3 High `a3-highgpu-8g` (8× H100) | USD 88.49/h | USD 64,698/mes | **No recomendado para bootstrap** |

**Lectura.** El MVP no necesita H100. Diseñar para L4 / A100 puntual.

### 6.6 Modelo de datos: principios FHIR

Recursos FHIR core para Fase 1:

- `Patient` — gestante / neonato / niño
- `Encounter` — consulta, parto, admisión UCIN, cesárea
- `Observation` — labs, signos vitales, mediciones
- `Condition` — diagnósticos, riesgos identificados
- `DiagnosticReport` — ecografías, reportes de laboratorio
- `Procedure` — cesárea, parto, tamizaje neonatal
- `CarePlan` — plan prenatal, plan CRED
- `Appointment` — controles prenatales, citas CRED
- `Practitioner` / `PractitionerRole` — médicos del partner

**Relación madre-neonato:** representada via `Patient.link` (tipo `seealso`) + recurso `FamilyMemberHistory` cuando aplica. **Decisión a confirmar en Fase 2 con asesor FHIR.** `[TODO]`

---

## 7. Validación clínica

### 7.1 Filosofía: riesgo incremental

Marco base: IMDRF (validez científica + desempeño analítico + desempeño clínico) + principios OMS (autonomía humana, transparencia, responsabilidad, beneficio público). `[CITADO — deep research §7]`

### 7.2 Plan de validación por etapa

| Etapa | Qué se valida | Diseño |
|---|---|---|
| **Retrospectiva** (R0) | Exactitud de resumen, extracción, care gaps, handoff | Benchmark sobre historias desidentificadas + doble revisión clínica de 2 médicos |
| **Shadow mode** (R2) | Seguridad operacional y calidad sin impacto en atención | Sistema corre en paralelo, no se muestra al médico o se muestra sin uso mandatorio |
| **Piloto asistivo** (R3, R4) | Aceptación médica y ahorro de tiempo | Médicos aceptan / editan / rechazan cada output |
| **Despliegue controlado** (R5) | Impacto en flujo y calidad | Seguimiento prospectivo de KPIs por servicio |
| **Expansión** (post-18m) | Generalización intersede e interespecialidad | Validación sitio por sitio |

### 7.3 Métricas de validación

| Caso de uso | Métrica primaria | Umbral interno objetivo |
|---|---|---:|
| Resumen longitudinal | Exactitud factual por span / omisiones críticas | >95% en hechos críticos |
| Extracción documental | F1 macro por campo clínico | >0.90 en campos críticos |
| Care gaps | Recall de brechas relevantes | >0.90 |
| Handoff materno-neonatal | Completitud de datos críticos | >95% |
| Brief preanestésico | Completitud + tasa de corrección crítica | <10% correcciones críticas |
| Adopción | Tasa de aceptación / edición ligera | >60% |

### 7.4 Explainability como requisito de diseño

Cada sugerencia incluye:
- dato fuente
- documento u observación que soporta
- timestamp
- contexto de especialidad
- nivel de confianza

Si no hay evidencia: **"no encontrado"**, nunca alucinación.

---

## 8. Marco regulatorio peruano

### 8.1 Tres frentes regulatorios para Fase 1

En orden de prioridad **para SICA** (no para toda la industria):

1. **Protección de datos personales (Ley 29733)** — el más urgente.
2. **Historia clínica electrónica (RENHICE + SIHCE)** — define cómo nos integramos.
3. **DIGEMID / software como dispositivo médico** — define qué podemos claim-ear.

### 8.2 Protección de datos (Ley 29733 y reglamento)

Obligaciones clave `[CITADO — deep research §7]`:

- **Consentimiento libre, previo, expreso, inequívoco e informado.** Para datos sensibles (salud), **debe constar por escrito**.
- **Inscripción del banco de datos personales** ante la ANPD.
- **Designación de Oficial de Datos Personales** (DPO) — recomendado cuando hay tratamiento de gran volumen o datos sensibles. SICA cumple ambos criterios.
- **DPIA (evaluación de impacto)** — facultativa pero recomendable para tratamientos de datos sensibles.
- **Medidas de seguridad documentadas.**
- **Plazos de respuesta a derechos del titular** (acceso, rectificación, supresión, oposición).
- **Mensajería no institucional** (WhatsApp, correos personales) debe estar formalmente aprobada — relevante porque clínicas peruanas usan WhatsApp informalmente.

**Acciones para SICA Fase 1:**
- Inscripción de banco de datos antes del primer piloto con datos reales.
- Designación de DPO (fraccional o asumido por un responsable capacitado — `[TODO: confirmar con asesor legal si fraccional es defendible en auditoría]`).
- DPIA documentado antes de R1.
- Plantillas de consentimiento clínico revisadas por abogado especializado.

### 8.3 RENHICE y SIHCE

- **Ley 30024 (RENHICE)** + reglamento 2025.
- **Directiva de acreditación SIHCE** aprobada marzo 2025, plazos ampliados 2026.
- **SIHCE requiere firma digital** para ser considerado tal.

**Posicionamiento de SICA:** **"capa copiloto interoperable sobre el SIHCE/EHR existente"**, no "nuevo SIHCE". Esto evita la obligación directa de acreditación del SIHCE recayendo en SICA — pero `[TODO: validar con asesor regulatorio si una capa que escribe datos en el SIHCE del partner queda sujeta a alguna acreditación derivada]`.

### 8.4 DIGEMID y software como dispositivo médico

`[CITADO — normativa peruana, deep research §7]`

La definición peruana de dispositivo médico incluye **"aplicativo informático"** cuando el fabricante lo destina a:
- diagnóstico
- prevención
- monitoreo
- tratamiento
- alivio o compensación

**Implicación para SICA:**

- Si SICA se posiciona como "diagnostica", "clasifica enfermedad", "detecta patología" → entra órbita DIGEMID.
- Si SICA se posiciona como **resumen, recuperación, checklist, documentación, soporte con confirmación médica obligatoria** → se mantiene como software asistivo.

**Posición de Fase 1:** claims estrictamente asistivos. Validación clínica antes de ampliar claims. Confirmación obligatoria del médico en cada output.

**`[TODO crítico]`** — la clasificación exacta para un copiloto no autónomo no aparece detallada en una guía pública peruana específica encontrada en el deep research. **Debe validarse con asesor regulatorio local antes de expandir claims hacia "detección de riesgo" en R2-R3.**

### 8.5 Telemedicina

Norma Técnica de Telesalud 2025 existe. **SICA Fase 1 no toca telemedicina** — añade superficie regulatoria innecesaria.

### 8.6 Residencia de datos

`[TODO crítico]` — el deep research no encontró obligación pública específica de residencia de datos en Perú para este caso. **Antes de desplegar PHI fuera del país (uso de Gemini cloud, por ejemplo) — validar contractual y legalmente.**

---

## 9. Go-to-market

### 9.1 ICP (Ideal Customer Profile)

**Clínica privada peruana mediana** con:

- Servicios completos materno-infantiles: ginecología, obstetricia, medicina fetal, pediatría, neonatología, UCIN, centro obstétrico, centro quirúrgico, anestesiología, emergencia gineco-obstétrica 24/7.
- 200–800 partos/año.
- HIS o SIHCE existente (cualquier nivel de madurez).
- Director médico con autonomía operativa de decisión.
- Disposición a pagar piloto, no solo POC gratis.

### 9.2 Motion comercial

| Etapa | Qué vender | A quién | Promesa |
|---|---|---|---|
| Entrada | Piloto pagado 8–12 semanas | Dirección médica + jefe obstetricia/neonatología + TI | Menos tiempo de revisión + mejor handoff |
| Expansión interna | Materno + anestesia + neonatología | Calidad / operaciones | Mejor completitud documental + menos omisiones |
| Expansión de sede | Repetición en otra sede / red | Gerencia corporativa | Estandarización + benchmarking |
| Fase B2C | Companion de alta | Clínica (no consumidor directo) | Extensión de valor B2B ya probado |

### 9.3 Discurso comercial

> **"SICA no reemplaza su HIS. Es una capa de inteligencia clínica que se monta sobre lo que ya tienen, reduce el tiempo de revisión de historia, mejora el handoff entre obstetricia y neonatología, y deja trazabilidad completa para calidad y auditoría."**

### 9.4 Pricing (sugerido, validar con 10-15 entrevistas)

`[ASUMIDO — deep research §9]`

| Plan | Alcance | Precio sugerido |
|---|---|---:|
| Piloto clínico | 1 sede, hasta 10 médicos, 8–12 semanas, 2 workflows | Setup USD 6,000 + USD 1,200/mes |
| Materno-Neo Core | 1 sede, hasta 30 médicos, 5 workflows, analytics básicos | Setup USD 10,000 + USD 2,800/mes |
| Red / Enterprise | Multisede, SSO, SLA, dashboards corporativos | Setup desde USD 20,000 + desde USD 6,500/mes |

### 9.5 Adopción médica real

Reglas operativas:

- Acceso con un clic desde la historia
- Resumen listo **antes** de la consulta / procedimiento
- Output siempre editable
- Evidencia visible (nunca caja negra)
- Sin copy-paste largo
- Shadow mode antes de uso mandatorio
- Champions médicos por especialidad
- Comité quincenal de feedback con clínicos + TI

---

## 10. Modelo de negocio y proyecciones

### 10.1 Modelo de negocio

**Clinical workflow SaaS B2B.** Unidad económica: la sede clínica o servicio (no el usuario consumidor).

Ingresos componentes:
1. Setup de integración (one-time)
2. Licencia mensual SaaS
3. Servicios de adaptación / validación clínica

Etapa posterior: componente B2C white-label (companion de alta) — no en modelo inicial.

### 10.2 Supuestos financieros

`[ASUMIDO — todo este bloque es modelo de trabajo del deep research, NO datos de mercado peruano validados]`

| Supuesto | Valor base |
|---|---:|
| Ticket piloto total | USD 9,600–10,800 |
| Ticket core anualizado | ~USD 43,600 (incl. setup primer año) |
| Margen bruto año 1 | 62% |
| Margen bruto año 2 | 70% |
| Margen bruto año 3 | 77% |
| CAC founder-led temprano | USD 6,000–8,000 |
| Churn anual al estabilizarse | 12–18% |
| LTV conservador | USD 90,000–110,000 |
| Ciclo de venta | 3–6 meses |
| Tiempo a piloto técnico | 4–6 meses |

### 10.3 Proyección a 3 años

`[ASUMIDO — modelo, no forecast]`

| Año | Clientes al cierre | Ingresos | Margen bruto | Opex | EBITDA |
|---|---:|---:|---:|---:|---:|
| 1 | 3 | USD 62,000 | USD 38,000 | USD 170,000 | **-USD 132,000** |
| 2 | 8 | USD 238,000 | USD 167,000 | USD 260,000 | **-USD 93,000** |
| 3 | 18 | USD 655,000 | USD 504,000 | USD 390,000 | **USD 114,000** |

**Lectura crítica:** si pilotos no se convierten a contratos core antes del mes 12, el proyecto se queda como consultoría. Si sí convierten y expanden por sede/especialidad, break-even cerca del final de año 3.

**Cuestionamiento al modelo (mío, no del deep research):** la curva 3→8→18 con ciclo de venta 3-6 meses y founder-led implica un ritmo de cierre que rara vez se sostiene sin AE dedicado antes del mes 12. El hiring plan original ponía al AE en "mes 12+", lo que choca con la curva de Año 2. **Revisar antes de pitch.**

### 10.4 Presupuesto 18 meses

| Partida | Presupuesto |
|---|---:|
| Ingeniería producto e integración | USD 88,000 |
| ML / evaluación / labeling | USD 24,000 |
| Liderazgo clínico y validación | USD 27,000 |
| Legal, privacidad y seguridad | USD 18,000 |
| Cloud, software y herramientas | USD 22,000 |
| Ventas founder-led y pilotos | USD 16,000 |
| Contingencia | USD 18,000 |
| **Total 18 meses** | **USD 213,000** |

Con 2 pilotos pagados desde meses 6-8 + créditos cloud, requerimiento neto cae a **USD 120,000–140,000**.

### 10.5 Data moat

Defensibilidad del producto a largo plazo:

- **Longitudinal clinical memory** — corpus de historias materno-infantiles desidentificadas con ground truth de validación. Más sedes = mejor modelo.
- **Workflow intelligence** — qué workflows usan los médicos peruanos en la práctica, vs. los documentados en guidelines.
- **Physician interactions** — feedback estructurado de aceptación/edición/rechazo. Datos de RLHF de facto.
- **Semantic graphs** materno-infantiles locales.
- **Outcomes learning** — correlación de inputs con outcomes neonatales/pediátricos.
- **Explainability systems** — la trazabilidad de evidencia y razonamiento se vuelve activo regulatorio.

---

## 11. Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Claims demasiado agresivos | Empujan a régimen DIGEMID antes de tiempo | Mantener claims asistivos + validación obligatoria del médico |
| Falta de integración con HIS del partner | Producto fuera del flujo, baja adopción | Conectores ligeros + launch embebido desde R2 |
| Calidad de PDFs y datos caóticos | Outputs malos | Empezar por extracción + revisión humana + fallback manual |
| Resistencia médica | Bajo uso real | Shadow mode + champions + evidencia visible + edición fácil |
| Riesgo de privacidad / brecha | Frenazo legal y comercial | DPO + banco de datos inscrito + DPIA + separación de entornos + auditoría |
| Lock-in de proveedor IA | Costo o disrupción | Orquestación multi-modelo + capa de abstracción de modelos |
| Infraestructura sobredimensionada | Burn innecesario | Arquitectura para L4 / A100 puntual, no H100 |
| Falta de dataset local | Mala generalización | Validación retrospectiva con datos del partner antes de R1 |
| **Partner fundador no firma a tiempo** | Roadmap se desplaza 3-6 meses | Negociación paralela con 2-3 prospects desde Mes 0 |
| **MedGemma 4B no alcanza umbral en historias locales** | R0 falla, stack se reconsidera | Plan B definido: 27B text-only o Gemini default para PHI con políticas estrictas |
| **Modelo financiero optimista en conversión piloto→core** | Runway insuficiente Año 2 | Acelerar contratación de AE a mes 9-10, no mes 12 |

---

## 12. Equipo y hiring

### 12.1 Roles fundadores (Día 0)

| Rol | Tipo | Responsabilidad |
|---|---|---|
| CEO / Founder comercial | Full-time | Ventas founder-led, pilotos, fundraising |
| CTO / Founder ML | Full-time | Arquitectura, modelos, ingeniería |
| Líder clínico fundador o advisor | 0.2-0.4 FTE | Validación clínica, credibilidad médica, acceso a partners |

### 12.2 Hires por fase

| Momento | Rol | Tipo |
|---|---|---|
| Mes 2-3 | Full-stack / integration engineer | Full-time |
| Mes 4-6 | Clinical informaticist / QA clínico | Part-time o full-time |
| Mes 6-9 | Product designer / customer success inicial | Part-time |
| **Mes 9-10** | **AE / implementation lead** (`[adelantado respecto al deep research]`) | Full-time |
| Mes 9-12 | Security & compliance counsel | Fractional |
| Mes 12+ | MLOps engineer | Full-time según tracción |

### 12.3 Oficial de Datos Personales

Requerido por norma cuando hay tratamiento de gran volumen o datos sensibles (SICA cumple ambos). **Puede ser fraccional al inicio**, pero `[TODO: validar con asesor legal si esto es defendible en auditoría]`.

---

## 13. Lo que NO entra en Fase 1

Reafirmación de scope. Ninguno de estos features se construye en los primeros 18 meses, aunque suenen tentadores:

- Ambient scribe / dictado médico
- Clasificación / retrieval multimodal avanzado de imágenes
- Companion B2C
- Telemedicina / teleconsulta
- Diagnóstico autónomo de cualquier tipo
- Expansión Chile / Colombia / México
- Integración con seguros / pagos
- Marketplace de protocolos
- Mobile app nativa (la PWA del panel basta)

---

## 14. Pendientes críticos (TODOs)

Cosas que deben resolverse **antes** de pasar a Fase 2 o que bloquean ejecución:

### Críticos (bloqueantes)

- [ ] **Validación regulatoria con asesor DIGEMID local** sobre clasificación de SICA como software asistivo no dispositivo médico.
- [ ] **Validación con asesor legal de protección de datos** sobre: inscripción banco de datos, DPIA, DPO fraccional, plantillas de consentimiento.
- [ ] **Verificación de marca SICA en Indecopi** (riesgo de colisión con SICA – Sistema de Integración Centroamericana, aunque sea sector distinto).
- [ ] **Confirmación de partner fundador.** Sin partner, R0 no arranca.
- [ ] **Acceso a 150-200 historias obstétricas desidentificadas** para benchmark R0.
- [ ] **Análisis competitivo Perú/LatAm real.** Hipótesis actual: no hay competidor directo. Validar con field research.

### Importantes (no bloqueantes, resolver en primeros 90 días)

- [ ] Revisión de licencia del repo (propietaria cerrada vs. abierta).
- [ ] Decisión sobre residencia de datos: ¿toda inferencia local en Perú o se permite cloud regional?
- [ ] Decisión sobre modelado FHIR de relación madre-neonato (Patient.link, FamilyMemberHistory, otro).
- [ ] Validación de pricing con 10-15 entrevistas comerciales reales.
- [ ] Definición de plan B para R0 si MedGemma 4B no alcanza umbral.
- [ ] Definición de proceso de inscripción de banco de datos personales ante ANPD — timeline.

### Pendientes para narrativa de fundraising (cuando aplique)

- [ ] TAM / SAM / SOM con números peruanos y de LATAM defendibles.
- [ ] Pitch deck en formato a16z / YC.
- [ ] Cap table inicial.
- [ ] Estructura legal de la empresa (SAC peruana, holding US, otro).
- [ ] Comparación financiera con comparables (Abridge Series A, Nabla, Ambience).

---

**Fin del documento estratégico v0.1.**

Próximo paso: validar con asesor clínico y regulatorio, luego pasar a Fase 2 (construcción de monorepo y capa de ejecución).
