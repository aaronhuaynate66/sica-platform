# STRATEGY.md — SICA

**Sistema de Inteligencia Clínica Asistida**
**Versión 0.2 — Fase 1 (Consolidación estratégica)**
**Última actualización:** 2026-05-20

---

## Cómo leer este documento

Este es el documento estratégico fundacional de SICA. Sirve tres audiencias en este orden:

1. **Founders y equipo interno** — para alinear decisiones de producto, ingeniería y comercial.
2. **Asesores externos** (clínico, regulatorio, legal) — para que validen supuestos críticos antes de construir.
3. **Inversores potenciales** — como base de pitch deck y narrativa de fundraising. La narrativa detallada VC vive en `docs/fundraising-narrative.md`.

**Convención:**
- `[TODO]` señala trabajo pendiente que NO debe inventarse — requiere investigación real, entrevistas o validación externa.
- `[ASUMIDO]` señala supuesto de trabajo que ordena el plan pero debe validarse con dato local.
- `[CITADO]` señala dato anclado en fuente verificable (ENDES, MINSA, etc.).

**Status del documento:** borrador interno. No compartir fuera del equipo hasta versión 1.0.

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Tesis: SICA como Clinical Intelligence Infrastructure](#2-tesis-sica-como-clinical-intelligence-infrastructure)
3. [Why Now: convergencia que hace posible SICA en 2026](#3-why-now-convergencia-que-hace-posible-sica-en-2026)
4. [Del wedge a la categoría](#4-del-wedge-a-la-categoría)
5. [Problema y validación de mercado](#5-problema-y-validación-de-mercado)
6. [Producto: visión y capacidades core](#6-producto-visión-y-capacidades-core)
7. [Roadmap de producto R0–R5](#7-roadmap-de-producto-r0r5)
8. [Distribution Engine](#8-distribution-engine)
9. [Clinical Data Flywheel](#9-clinical-data-flywheel)
10. [AI Evaluation Infrastructure](#10-ai-evaluation-infrastructure)
11. [Arquitectura técnica](#11-arquitectura-técnica)
12. [Validación clínica](#12-validación-clínica)
13. [Marco regulatorio peruano](#13-marco-regulatorio-peruano)
14. [Go-to-market](#14-go-to-market)
15. [Modelo de negocio y proyecciones](#15-modelo-de-negocio-y-proyecciones)
16. [Expansion Logic post-18m](#16-expansion-logic-post-18m)
17. [Platform Strategy (horizonte año 3+)](#17-platform-strategy-horizonte-año-3)
18. [Riesgos y mitigación](#18-riesgos-y-mitigación)
19. [Equipo y hiring](#19-equipo-y-hiring)
20. [Lo que NO entra en Fase 1](#20-lo-que-no-entra-en-fase-1)
21. [Pendientes críticos (TODOs)](#21-pendientes-críticos-todos)

---

## 1. Resumen ejecutivo

**SICA construye la primera infraestructura de inteligencia clínica longitudinal para salud materno-infantil en mercados emergentes**, empezando por Perú.

No es un EHR. No es un chatbot. No es una herramienta de automatización. Es una **categoría nueva**: Clinical Intelligence Infrastructure — la capa cognitiva que conecta longitudinalmente embarazo, parto, neonatología y pediatría, y que se monta sobre los HIS y SIHCE existentes sin reemplazarlos.

**Por qué ahora.** Convergen ocho fuerzas que hacían SICA imposible en 2022 y que en 2026 lo hacen no solo posible sino urgente: la madurez de los LLMs médicos open-weight (MedGemma), el colapso de costos de inferencia, la consolidación de FHIR R4, la primera Conectatón nacional peruana en 2025, la nueva acreditación SIHCE, el burnout clínico, la escasez médica en LatAm, y una nueva generación de médicos digital-native. § 3 desarrolla cada una.

**El wedge táctico** es deliberadamente humilde: resumen longitudinal obstétrico + handoff materno-neonatal en una clínica privada fundadora en Lima. **El destino estratégico** es construir la infraestructura cognitiva del journey clínico materno-infantil completo y eventualmente expandirla a otras especialidades longitudinales (cardiología, oncología, salud mental). § 4 explica cómo el wedge construye la categoría.

**Por qué SICA puede ganar:**

1. **Posicionamiento "asistido" como ventaja regulatoria estructural.** El claim está construido en el branding. No diagnostica, no decide, no es autónomo. Mantiene a SICA fuera de la órbita DIGEMID en Fase 1.
2. **Arquitectura multimodal interoperable desde día uno.** FHIR R4 como backbone canónico, MedGemma local como default para PHI, Gemini como escalamiento puntual, MedSigLIP para retrieval visual. No es lock-in con un solo proveedor.
3. **Doctor-in-the-loop por diseño, no por marketing.** Cada output muestra evidencia trazable, timestamp, nivel de confianza. El médico edita o rechaza. Auditoría completa.
4. **B2B antes de B2C, vertical antes de horizontal.** El primer presupuesto a capturar es clínico-operacional en una vertical específica. La expansión a otras especialidades y al companion materno B2C llega después de probar adopción en el wedge.
5. **Data flywheel como moat estructural.** Cada uso genera datos longitudinales que ningún modelo entrenado en US/EU tiene. § 9 desarrolla los loops específicos.
6. **Distribution Engine clínico**, no solo go-to-market. Sociedades médicas peruanas, KOLs, residencias, congresos, research partnerships — sistema, no táctica. § 8.

**Métricas de éxito a 18 meses:**
- 1 partner fundador con SICA en producción shadow + asistivo en obstetricia, neonatología y anestesia.
- Sede 2 firmada con plan Materno-Neo Core.
- Benchmark clínico documentado: >95% exactitud factual en resumen obstétrico, >95% completitud en handoff materno-neonatal.
- Renovación anual del partner fundador.
- Al menos 3 KOLs clínicos peruanos como advisors o co-investigadores formales.
- Primer paper o póster en congreso peruano de obstetricia o pediatría.

**Capital requerido para 18 meses:** USD 213,000 brutos, potencialmente USD 120,000–140,000 netos con dos pilotos pagados desde mes 6–8 y créditos cloud. `[ASUMIDO]`

---

## 2. Tesis: SICA como Clinical Intelligence Infrastructure

### 2.1 La categoría que SICA construye

La industria de software médico se ha organizado históricamente en tres capas:

1. **Sistemas de registro** (HIS, EHR, SIHCE) — guardan lo que pasó.
2. **Sistemas de procesamiento** (LIS, PACS, RIS) — procesan dominios específicos.
3. **Sistemas de comunicación** (mensajería clínica, referencias) — mueven información.

Lo que falta — y lo que SICA construye — es una **cuarta capa**: el **sistema de inteligencia clínica**. Una capa cognitiva que:

- **lee** todo lo que las capas 1-3 produjeron,
- **conecta** datos dispersos en una memoria longitudinal,
- **razona** sobre patrones, riesgos, brechas y handoffs,
- **explica** cada inferencia con evidencia trazable,
- **asiste** al médico sin reemplazarlo.

Esta capa no existe hoy en ningún mercado emergente. En US existe parcialmente (Epic con sus módulos de AI, Abridge en scribe, Glass Health en reasoning), pero ningún player la ha construido como **infraestructura vertical longitudinal especializada**.

**SICA construye esa categoría empezando por el dominio donde más se necesita en Perú: salud materno-infantil.**

### 2.2 Posicionamiento contra incumbents

| Categoría existente | Ejemplo | Por qué SICA es diferente |
|---|---|---|
| EHR / HIS / SIHCE | Epic, Athenahealth, sistemas peruanos | SICA no almacena el sistema de verdad — lee de él y lo enriquece |
| Ambient scribe | Abridge, Nabla, Suki, Ambience | SICA no transcribe consultas — construye memoria longitudinal con datos ya existentes |
| Clinical reasoning chatbot | Glass Health, OpenEvidence | SICA no responde preguntas médicas genéricas — asiste workflows clínicos específicos con datos del paciente |
| Knowledge retrieval | UpToDate, OpenEvidence | SICA no es biblioteca de evidencia — es memoria del paciente individual |
| Patient-facing health app | Cualquier app de embarazo | SICA es B2B clínico, no consumer |
| Automation / RPA clínica | Players de automatización administrativa | SICA es razonamiento, no automatización de tareas |
| HIS analytics | Tableau-style sobre datos hospitalarios | SICA es prospectivo (point-of-care), no retrospectivo (dashboards) |

**El framing oficial:**

> _"SICA es Clinical Intelligence Infrastructure — la capa cognitiva longitudinal que conecta el journey clínico materno-infantil completo, montada sobre los sistemas existentes, con explainability y doctor-in-the-loop por diseño."_

### 2.3 Qué SICA NO es

| No es | Por qué importa la distinción |
|---|---|
| Un sistema de diagnóstico autónomo | Cambia clasificación regulatoria a dispositivo médico DIGEMID, dispara validación clínica formal larga y costosa |
| Un chatbot médico para pacientes | Mercado distinto, riesgo regulatorio distinto, no es B2B clínico |
| Una app de embarazo / pregnancy tracker | El comprador es la madre, no la clínica. Modelo de negocio distinto |
| Un HIS / EHR de reemplazo | Ciclo de venta de 18+ meses, costo de implementación 10x, no es bootstrap-able |
| Una plataforma de telemedicina | Norma Técnica de Telesalud 2025 añade superficie regulatoria; el wedge inicial es presencial |
| Un CRM o automatización administrativa | Mercado distinto, valor distinto |
| Un ambient scribe genérico | Categoría madura en US con incumbents bien financiados; SICA compite en un eje diferente |

### 2.4 Filosofía de producto

Cuatro principios no negociables:

1. **Doctor-in-the-loop.** Ningún output llega a flujo crítico sin confirmación médica explícita.
2. **Explainability-first.** Cada hecho viene con fuente, timestamp y confianza. Si no hay evidencia, el sistema dice "no encontrado" — no rellena.
3. **Regulatory-aware.** Cada feature pasa filtro regulatorio antes de pasar filtro de utilidad.
4. **Clinically grounded.** Las métricas de éxito las define el médico, no el growth team.

---

## 3. Why Now: convergencia que hace posible SICA en 2026

Cualquier startup elite necesita timing narrative. Para SICA, ocho fuerzas convergen en 2026 que estaban ausentes o inmaduras en 2022. Cada una sola no justificaría la apuesta; las ocho juntas la hacen urgente.

### 3.1 LLMs médicos open-weight son reales

Hasta 2024, construir un copiloto clínico significaba (a) llamar a GPT-4 con todos los problemas de PHI en cloud no especializado, o (b) entrenar desde cero con datos clínicos —imposible para una startup early-stage—. En 2024 Google liberó MedGemma (4B multimodal, 27B text-only) y MedSigLIP. Por primera vez una startup puede correr inferencia médica de calidad **localmente, sobre PHI, sin enviar datos a un proveedor cloud genérico**. Esta sola condición habilita Perú/LatAm donde residencia de datos es ambigua y la sensibilidad pública sobre fuga de datos médicos es alta.

### 3.2 Multimodal AI llegó a madurez productiva

Gemini 2.5 entiende PDFs nativamente (no solo OCR — comprende estructura, tablas, figuras). MedSigLIP genera embeddings médicos visuales sin alucinación porque no genera texto. Esta combinación significa que SICA puede procesar **el formato real de los datos clínicos peruanos** (PDFs escaneados, ecografías con texto incrustado, reportes mal estructurados) sin construir pipelines artesanales para cada formato.

### 3.3 Costos de inferencia colapsaron

Una GPU NVIDIA L4 en Google Cloud cuesta USD 0.71/hora `[CITADO]`. Eso son ~USD 516/mes de inferencia 24/7 — alcance para un MVP completo. En 2022 una infraestructura comparable habría requerido A100s a USD 3,000+/mes. **El costo unitario por consulta procesada cayó >10x en 24 meses**, abriendo modelos de negocio que antes eran imposibles para healthtech en mercados emergentes.

### 3.4 FHIR R4 dejó de ser proyecto y empezó a ser estándar

En 2024-2025 FHIR R4 consolidó adopción en US (CMS interoperability rule), EU (EHDS) y empezó a aparecer en LatAm. En Perú, la **primera Conectatón nacional de interoperabilidad de HCE ocurrió en junio 2025** `[CITADO]`, marcando el inicio operativo del estándar. SICA puede apostar a FHIR como backbone canónico sin riesgo de que el estándar cambie debajo en los próximos 5 años.

### 3.5 Perú aceleró el marco regulatorio de salud digital

- **Ley 30024 RENHICE** con reglamento actualizado en 2025.
- **Directiva de acreditación SIHCE** aprobada marzo 2025, plazos ampliados 2026.
- **Conectatón nacional** junio 2025.

Esto crea una ventana específica: **el ecosistema peruano está en transición activa pero el estándar aún no está maduro**. Un integrador clínico útil que llegue ahora puede definir la práctica antes de que la capa estándar se consolide. Si SICA llega en 2028, el espacio ya está ocupado.

### 3.6 Burnout clínico y escasez médica son cuantificables

`[TODO — buscar dato peruano específico de burnout en obstetricia/neonatología]`

Globalmente: Medscape Physician Burnout Report consistentemente reporta tasas >50% en especialidades de alta carga (obstetricia, urgencias, pediatría). En Perú, escasez de neonatólogos y anestesiólogos en regiones es estructural. Un copiloto que reduce tiempo de revisión de historia y handoff es una respuesta directa, medible.

### 3.7 Fragmentación clínica extrema en LatAm

A diferencia de US donde Epic concentra 30%+ del mercado hospitalario, en Perú coexisten decenas de HIS heredados, integraciones parciales, papel, PDFs escaneados, CSVs y WhatsApp informal. **Esa fragmentación, que parece debilidad, es la oportunidad de SICA**: una capa de inteligencia que normaliza y conecta no tiene incumbent local, porque ningún HIS dominante puede construirla.

### 3.8 Nueva generación de médicos digital-native

Los médicos en formación hoy (residentes 2024-2028) crecieron con UpToDate móvil, ChatGPT durante la pandemia, y expectativa de herramientas como Linear y Notion en su trabajo. **La resistencia cultural a copilotos clínicos que dominó 2015-2020 está colapsando** entre médicos <40. El partner fundador correcto tiene champions de esta generación.

### 3.9 Síntesis del Why Now

Ninguna fuerza por sí sola justifica la apuesta. Pero la convergencia de las ocho crea una ventana de ~3 años (2026-2029) donde:

- la tecnología está madura,
- los costos son alcanzables para bootstrap,
- el estándar de datos está consolidándose,
- el marco regulatorio peruano está abriéndose,
- la demanda clínica es urgente,
- el incumbent local no existe,
- y los médicos de nueva generación están listos para adoptarlo.

**Después de esta ventana, alguien construye SICA. La pregunta es si los founders correctos lo hacen primero.**

---

## 4. Del wedge a la categoría

Una tensión aparente en este documento: la sección 1 habla de "Clinical Intelligence Infrastructure, categoría billion-dollar" y la sección 7 describe un wedge muy específico — "resumen longitudinal obstétrico en una clínica peruana". ¿Cómo se concilian?

**No son contradictorios. Son la misma cosa en dos resoluciones temporales.**

### 4.1 La cadena que conecta wedge y categoría

```
Wedge táctico                          Categoría estratégica
─────────────                          ─────────────────────
Resumen obstétrico    ─┐
(R1, Mes 2-5)          │
                       │
Checklist prenatal    ─┤
(R2, Mes 5-8)          │      Estos cinco componentes,
                       │      operando juntos, son
Handoff materno-neo   ─┼───→  el Clinical Memory Graph
(R3, Mes 8-11)         │      + Reasoning Engine
                       │
Brief preanestésico   ─┤      ↓
(R4, Mes 11-14)        │
                       │      Eso es Clinical Intelligence
Pediatría/CRED        ─┘      Infrastructure para salud
(R5, Mes 14-18)               materno-infantil.
```

Cada release táctico no es un feature aislado — es un **loop de datos** que alimenta los siguientes:

- El **resumen obstétrico** (R1) construye el corpus inicial del Memory Graph: timelines, problemas activos, evidencia trazable.
- El **checklist prenatal** (R2) entrena el Reasoning Engine en detección de brechas sobre ese corpus.
- El **handoff materno-neonatal** (R3) extiende el grafo del paciente individual a una **relación clínica multi-paciente** (madre↔bebé).
- El **brief preanestésico** (R4) prueba que el Reasoning Engine puede operar bajo presión temporal real (cesárea de emergencia).
- El **módulo CRED** (R5) cierra el loop longitudinal: el bebé seguido en pediatría hereda contexto del handoff, validando continuidad real.

**Cuando el R5 está en producción y el partner fundador renueva en plan Core, SICA ya no es "una herramienta de resumen". Es la primera infraestructura de inteligencia clínica longitudinal materno-infantil en LatAm.** Eso es categoría nueva.

### 4.2 Por qué este orden no es opcional

El error clásico de healthtech AI es vender "plataforma" antes de tener producto, o construir "infraestructura" sin un caso de uso que la justifique. SICA evita ese error porque cada release táctico **es** un caso de uso vendible Y al mismo tiempo **es** un componente de la infraestructura.

No estamos construyendo el Memory Graph como proyecto interno de 18 meses y vendiendo "resumen obstétrico" como producto mientras tanto. **Estamos construyendo el resumen obstétrico, que ES la primera capa del Memory Graph.** Cuando R5 termina, no hay un "pivot a plataforma" — hay una continuación natural de lo que se construyó desde R1.

### 4.3 Comunicación según audiencia

| Audiencia | Cómo se cuenta |
|---|---|
| Director médico del partner fundador | "Reducimos el tiempo de revisión de historia obstétrica de 8 minutos a 2." |
| Jefe de neonatología | "El handoff materno-neonatal te llega completo en 60 segundos." |
| Champion obstetra | "Tu resumen está listo antes de que entres a consulta." |
| Inversor seed peruano | "Clinical workflow SaaS materno-infantil, primer wedge probado, expansión clara." |
| Inversor Series A US (a16z, GV, Founders Fund) | "Clinical Intelligence Infrastructure para salud materno-infantil en mercados emergentes, con data flywheel longitudinal y posicionamiento regulatorio defendible." |
| Asesor regulatorio peruano | "Software asistivo de documentación, recuperación y soporte contextual, con confirmación médica obligatoria." |

**Los seis discursos son verdaderos. Son la misma empresa contada con el lenguaje que cada audiencia entiende y valida.**

---


## 5. Problema y validación de mercado

### 5.1 Carga clínica que justifica el producto

En Perú, la salud materno-infantil sigue siendo prioridad pública. Indicadores relevantes `[CITADO — MINSA / ENDES]`:

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

### 5.2 El problema reformulado en lenguaje SICA

El journey clínico materno-infantil atraviesa 5+ servicios y 3+ años de continuidad. Hoy ese journey vive fragmentado:

| Etapa | Dónde vive el dato | Quién lo necesita después | Fricción |
|---|---|---|---|
| Embarazo | Notas obstétricas, ecografías, labs en PDFs | Obstetra de guardia, anestesiólogo, neonatólogo | Reconstruir cada vez |
| Parto | Sala de partos, registros separados | Neonatólogo en recepción | Handoff verbal/papel |
| Neonatal | UCIN, tamizajes, hoja neonatal | Pediatra ambulatorio | Pérdida de contexto al alta |
| Pediatría 0-2 años | CRED, vacunas, controles | Pediatra futuro, especialista si aparece patología | Múltiples sistemas, papel |
| Pediatría 2-5 años | Continuidad de CRED, anemia, desarrollo | Médico ante cualquier consulta | Sin línea de tiempo unificada |

**Cada transición pierde información.** Cada pérdida aumenta carga cognitiva, errores potenciales, tiempo improductivo. SICA es la memoria longitudinal que no se pierde en las transiciones.

### 5.3 Usuarios objetivo

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

## 6. Producto: visión y capacidades core

SICA se construye sobre **cinco capacidades** que interactúan. Estas no son features sueltas — son los componentes de la categoría Clinical Intelligence Infrastructure.

### 6.1 Clinical Memory Graph

Memoria clínica longitudinal que conecta antecedentes, evolución, síntomas, labs, ecografías, procedimientos, riesgos, timelines gestacional y neonatal, crecimiento pediátrico, evolución anestésica, outcomes.

Implementada con knowledge graph + vector memory + embeddings médicos + temporal reasoning. **La clave técnica diferenciadora:** el grafo no es solo del paciente individual — incluye relaciones clínicas (madre↔bebé, hermanos cuando aplica, contexto familiar relevante) y temporales (cómo evolucionó un riesgo a lo largo del embarazo).

### 6.2 Clinical Reasoning Engine

Motor que detecta patrones, correlaciona datos, sugiere hipótesis diferenciales, detecta riesgos longitudinales, encuentra inconsistencias, prioriza señales.

**NO diagnostica. Decision support, no decision making.** Cada inferencia incluye: evidencia trazable, nivel de confianza, abstención cuando no hay evidencia suficiente.

### 6.3 Multimodal Ingestion Layer

Extracción estructurada desde PDFs nativos y escaneados, ecografías con texto incrustado, reportes manuscritos, HL7v2, FHIR parcial, CSV, formularios institucionales. OCR médico + parsers especializados + extracción estructurada con LLM cuando la heurística falla.

**Realidad peruana:** la mayor parte del input no es FHIR. Es PDFs. La capa de ingesta es donde se gana o se pierde la batalla de adopción.

### 6.4 Explainability Layer

Cada output médico incluye razonamiento, evidencia, variables relevantes, correlaciones detectadas, referencias clínicas, guideline relacionada, confidence scoring.

**Esto no es feature opcional. Es requisito de licencia social.** Sin explainability un médico no confía, sin confianza no usa, sin uso no hay data flywheel, sin flywheel no hay moat.

### 6.5 Physician Copilot UI

UX optimizada para minimizar carga cognitiva. Embed en HIS (launch button contextual), respuesta <2 segundos en pre-consulta, output siempre editable, evidencia visible.

Inspiración deliberada: **Linear** (velocidad), **Notion** (estructura), **Bloomberg Terminal** (densidad informacional para profesionales), **Palantir Gotham** (capa cognitiva sobre datos complejos).

### 6.6 Capa B2C futura (no Fase 1)

Companion para madres post-alta, seguimiento infantil, AI educational, reminders. **Siempre conectado al sistema clínico**, nunca como producto consumer aislado. Diseñar arquitectura pensando en esto desde día uno aunque no se construya hasta post-mes 18.

---

## 7. Roadmap de producto R0–R5

Resumen del roadmap a 18 meses. Detalle completo en [`docs/roadmap.md`](docs/roadmap.md).

**Principios:**

1. Cada release pasa un **gate clínico/técnico** antes de pasar al siguiente.
2. El primer release **no es un feature, es un benchmark**.
3. **Shadow mode es la barrera natural entre alpha y beta.**
4. Cada release **es** un componente del Memory Graph / Reasoning Engine, no un feature aislado.

| Release | Mes | Wedge | Gate clave de salida | Qué construye en la categoría |
|---|---|---|---|---|
| **R0 Foundation** | 0–2 | Benchmark + stack mínimo | MedGemma 4B ≥85% factualidad, ≤5% omisiones | Validación técnica de la apuesta de modelos |
| **R1 Resumen Obstétrico (Alpha)** | 2–5 | Panel standalone, sesiones de revisión | >70% resúmenes útiles | Primera capa del Memory Graph: timelines + evidencia |
| **R2 Shadow + Checklist** | 5–8 | Embed en HIS, no mandatorio | ≥40% uso + recall brechas ≥80% | Reasoning Engine entrenado en detección de brechas |
| **R3 Handoff Materno-Neonatal** | 8–11 | Primer flujo crítico (asistivo) | Completitud ≥95% + correcciones <10% | Memory Graph multi-paciente (madre↔bebé) |
| **R4 Brief Preanestésico** | 11–14 | Cesárea programada y urgencia | <10% correcciones críticas + aprobación calidad | Reasoning Engine bajo presión temporal real |
| **R5 CRED + Multi-sede** | 14–18 | Pediatría longitudinal + producto replicable | Sede 2 onboarded + renovación | Continuidad longitudinal completa + escala |

### 7.1 Decisiones explícitas dentro del roadmap

- **R3 (handoff neonatal) antes que R4 (brief anestésico).** Razón: menor riesgo legal (handoff pasa información, brief preanestésico toca decisión farmacológica), y ROI más visible para dirección médica. `[Revisable si partner tiene volumen de cesárea programada significativamente mayor a UCIN]`.
- **R0 de 2 meses asume que el partner ya firmó acceso a datos.** Si no, R0 se extiende a 3 meses.
- **CRED al final, no antes.** Depende de continuidad longitudinal real desde R3.

---

## 8. Distribution Engine

Distribución mata producto. Hasta el mejor copiloto clínico fracasa si no hay un sistema deliberado para entrar en clínicas, construir credibilidad médica y disparar adopción orgánica. SICA opera con un **Distribution Engine clínico** desde el mes 1, no como táctica reactiva.

### 8.1 Capas del Distribution Engine

| Capa | Mecanismo | Output esperado |
|---|---|---|
| **KOLs (Key Opinion Leaders)** | Identificar 5-10 líderes clínicos en obstetricia y neonatología peruana. Construir relación a través de research partnerships y advisory positions | 3 KOLs como advisors formales antes mes 12 |
| **Sociedades médicas** | Sociedad Peruana de Obstetricia y Ginecología (SPOG), Sociedad Peruana de Pediatría (SPP), Sociedad Peruana de Neonatología, Sociedad Peruana de Anestesiología. Membresía corporativa, sponsorships selectivos, presencia en comités técnicos | Reconocimiento institucional como interlocutor serio |
| **Champions clínicos** | En cada clínica donde SICA opera, identificar 1-2 médicos influyentes por especialidad que adopten temprano y eduquen pares | Cada champion = 3-5 médicos adicionales adoptan en 90 días |
| **Programas de residencia** | Partnerships con residencias de obstetricia, neonatología y pediatría en hospitales docentes. SICA como herramienta de aprendizaje en revisión de casos | Pipeline de médicos digital-native que llegan a clínicas privadas habiendo usado SICA |
| **Congresos médicos** | Presencia anual en congresos SPOG, SPP, Latin American Society of Perinatology. Booth + presentaciones técnicas + papers o pósters de validación clínica | Marca clínica establecida + lead generation calificada |
| **Research partnerships** | Co-investigación con uno o dos centros docentes sobre uso de IA asistiva en handoff materno-neonatal. Publicación conjunta | Validación académica + acceso a datos para evals |
| **Physician network effects** | Cada médico que adopta SICA puede invitar colegas. Sistema de referidos clínicos con incentivo no monetario (acceso anticipado a features, advisor program) | Crecimiento orgánico médico-a-médico |

### 8.2 Calendarización

| Periodo | Actividad Distribution Engine | Owner |
|---|---|---|
| Mes 0-3 | Identificar y contactar 5 KOLs target | CEO + Líder clínico |
| Mes 3-6 | Membresía SPOG + asistencia a congreso anual | Líder clínico |
| Mes 4-8 | Onboarding de 3-5 champions en partner fundador | Customer Success |
| Mes 6-12 | Research partnership formal con un centro docente | Líder clínico + CTO |
| Mes 9-12 | Primer póster o paper en congreso peruano | Líder clínico + equipo clínico |
| Mes 12-18 | Programa de advisors formales (3 KOLs firmados) | CEO |
| Mes 15-18 | Lanzamiento de programa de referidos médicos | Customer Success |

### 8.3 Por qué Distribution Engine y no "marketing"

Healthtech no se vende con ads digitales ni con SEO. Se vende a través de **legitimidad clínica** construida deliberadamente. Cada movimiento del Distribution Engine deposita capital en una de cuatro cuentas:

1. **Capital institucional** (sociedades médicas, congresos).
2. **Capital de pares** (KOLs, champions, network effects).
3. **Capital académico** (research partnerships, papers).
4. **Capital generacional** (residencias, médicos digital-native).

Cuando un director médico está evaluando SICA en el mes 14, las cuatro cuentas se activan a la vez. Esa es la diferencia entre cerrar un piloto en 2 semanas o en 4 meses.

---

## 9. Clinical Data Flywheel

El moat real de SICA no es el modelo ni la UI ni los conectores FHIR. Es el **dataset longitudinal materno-infantil peruano** que ningún player global tiene. Pero ese dataset solo se construye si hay un flywheel deliberado que conecta uso → datos → mejora → uso.

### 9.1 Los cinco loops del flywheel

```
                    ┌───────────────────────────────┐
                    │   1. Adoption Loop            │
                    │   Más uso clínico             │
                    │     ↓                         │
                    │   Más feedback estructurado   │
                    │   (aceptado/editado/rechazado)│
                    └────────────┬──────────────────┘
                                 ↓
                    ┌───────────────────────────────┐
                    │   2. Quality Loop             │
                    │   Más feedback                │
                    │     ↓                         │
                    │   Mejores prompts +           │
                    │   mejores embeddings +        │
                    │   mejor reasoning             │
                    └────────────┬──────────────────┘
                                 ↓
                    ┌───────────────────────────────┐
                    │   3. Trust Loop               │
                    │   Mejor reasoning             │
                    │     ↓                         │
                    │   Más confianza médica        │
                    │     ↓                         │
                    │   Más uso clínico             │
                    └────────────┬──────────────────┘
                                 ↓
                    ┌───────────────────────────────┐
                    │   4. Longitudinal Loop        │
                    │   Más uso a lo largo del time │
                    │     ↓                         │
                    │   Más datos longitudinales    │
                    │   madre↔bebé↔pediatría        │
                    │     ↓                         │
                    │   Único dataset que conecta   │
                    │   embarazo con CRED 3 años    │
                    │   después                     │
                    └────────────┬──────────────────┘
                                 ↓
                    ┌───────────────────────────────┐
                    │   5. Outcomes Loop            │
                    │   Más datos longitudinales    │
                    │     ↓                         │
                    │   Correlación inputs→outcomes │
                    │   (riesgo gestacional →       │
                    │    outcomes neonatales →      │
                    │    desarrollo pediátrico)     │
                    │     ↓                         │
                    │   Modelos predictivos únicos  │
                    │   que ningún player tiene     │
                    └───────────────────────────────┘
```

### 9.2 Qué dato cierra cada loop

| Loop | Dato que lo cierra | Release en que se activa |
|---|---|---|
| 1. Adoption | Eventos de aceptación/edición/rechazo por output | R1 (sesiones de revisión) → R2 (consulta real) |
| 2. Quality | Pares (output original, output corregido por médico) → fine-tuning + prompt versioning | R2 (volumen suficiente de feedback) |
| 3. Trust | Métricas de uso por médico, tiempo ahorrado autorreportado, willingness-to-recommend | R2-R3 |
| 4. Longitudinal | Vínculos madre↔bebé persistidos en el Memory Graph + seguimiento CRED del mismo bebé | R3 (vínculo) + R5 (continuidad) |
| 5. Outcomes | Outcomes neonatales (Apgar, peso, complicaciones) y pediátricos (CRED, anemia, desarrollo) correlacionados con inputs maternos | R5+ (volumen suficiente, post-18m con base instalada) |

### 9.3 Por qué este flywheel es defendible

Tres razones específicas:

1. **Es longitudinal materno-infantil, no transversal.** Un competidor que entre en obstetricia en 2027 puede generar volumen de resúmenes obstétricos. Pero no puede generar **datos de continuidad madre→bebé→CRED 3 años**. Esos datos requieren 3 años de calendario, no más capital.

2. **Es peruano, no extrapolado.** MedGemma fue entrenado en datos clínicos US/EU. Las prácticas obstétricas peruanas (paquete prenatal MINSA, criterios de cesárea, protocolos UCIN locales) difieren. El fine-tuning con datos peruanos es valor que se acumula con el uso.

3. **Es de feedback estructurado, no inferido.** Saber qué editó el médico y por qué (con razón categorizada) es señal de RLHF mucho más rica que click-through. El flywheel se acelera con datos cualitativos, no solo cuantitativos.

### 9.4 Riesgos del flywheel

- **Cold start.** Loop 1 requiere un partner que aporte volumen. Sin partner, el flywheel no arranca. (Mitigación: identificar partner con >300 partos/año.)
- **Data drift.** Si los protocolos del partner cambian (nueva guideline, cambio de criterios), el modelo entrenado en data antigua degrada. (Mitigación: monitoreo continuo + retraining trimestral.)
- **Privacy ceiling.** El flywheel asume que se puede agregar datos de múltiples clínicas eventualmente. Si la regulación peruana endurece residencia y prohibe agregación, el moat por sede se mantiene pero el moat agregado se debilita. (Mitigación: separación de entornos federados desde día uno.)

---

## 10. AI Evaluation Infrastructure

Si el Data Flywheel es el moat, la AI Evaluation Infrastructure es la garantía de calidad que lo sostiene. Es lo que separa una healthtech AI seria de un wrapper de LLMs.

### 10.1 Los siete pilares de la evaluación

| Pilar | Qué mide | Cómo |
|---|---|---|
| **1. Factual accuracy** | ¿El resumen contiene hechos verdaderos según la historia? | Span-level comparison contra ground truth creado por 2 médicos en doble ciego |
| **2. Critical omissions** | ¿El sistema omitió datos clínicamente relevantes? | Checklist de campos críticos por especialidad, calculado por output |
| **3. Hallucination benchmark** | ¿El sistema inventó información que no está en la historia? | Test set adversarial donde el ground truth incluye explícitamente "no encontrado" |
| **4. Physician disagreement scoring** | ¿Cuánto editan los médicos el output? ¿En qué dimensiones? | Tracking de ediciones categorizadas (factual, redacción, énfasis, omisión, alucinación) |
| **5. Longitudinal consistency** | ¿El sistema mantiene coherencia entre output sobre el mismo paciente en distintos momentos? | Test sobre series temporales de la misma paciente, comparando outputs entre encuentros |
| **6. Temporal reasoning** | ¿Razona correctamente sobre EG, FUM, FPP, ventanas críticas? | Test set sintético con casos diseñados para fallar en razonamiento temporal |
| **7. Synthetic patient testing** | ¿Generaliza a casos no vistos pero plausibles? | Pacientes sintéticos construidos por médicos para cubrir edge cases (preeclampsia atípica, RPM con corioamnionitis, gemelar con discordancia) |

### 10.2 Regression testing de prompts

Cada cambio de prompt (de cualquier feature) **debe pasar la suite completa antes de merge**. Sin esto, mejorar un prompt para resumen obstétrico puede romper silenciosamente el handoff neonatal. Esto es invisible sin infraestructura.

Componentes:

- **Prompt registry** versionado, con metadata (autor, fecha, descripción del cambio, métricas previas/posteriores).
- **Test set congelado** por capability, con casos representativos + adversariales + edge cases.
- **Gates automáticos en CI/CD** que bloquean merge si una métrica clave degrada >X% sin justificación documentada.
- **Rollback automático** si métricas en producción degradan tras deploy.

### 10.3 Physician disagreement scoring

Esta es la métrica más subestimada en healthtech AI y la más valiosa para SICA.

Cuando un médico edita el output, esa edición se categoriza:

| Categoría | Significado | Implicación |
|---|---|---|
| Factual fix | Corrige un hecho incorrecto | Señal de hallucination o extracción incorrecta — alta prioridad |
| Critical addition | Agrega algo que el sistema omitió | Señal de critical omission — alta prioridad |
| Style edit | Cambia redacción sin cambiar contenido | Señal de tono/estilo — prioridad baja, candidato a prompt tuning |
| Emphasis edit | Reordena o destaca info | Señal de UX, no de modelo — feedback a diseño |
| Removal | Quita algo que el sistema incluyó | Señal de verbosidad o info irrelevante — prompt tuning |

Cada categoría alimenta un loop diferente. Factual fixes alimentan retraining; emphasis edits alimentan diseño de UI. Sin esta categorización, todo el feedback se ve igual.

### 10.4 Synthetic patient testing

Antes de exponer SICA a un caso real de preeclampsia, hay que asegurar que el sistema maneja correctamente:

- preeclampsia clásica
- preeclampsia atípica (sin proteinuria pero con signos de daño orgánico)
- síndrome HELLP
- preeclampsia con eclampsia
- preeclampsia post-parto

Estos cinco escenarios se construyen como **historias sintéticas detalladas por médicos especialistas**, con ground truth explícito de qué debe el sistema detectar, qué riesgos debe alertar, qué brechas debe señalar.

La suite sintética crece con cada release y se mantiene como **regression test permanente**. Es el equivalente clínico de los test unitarios.

### 10.5 Hallucination detection en producción

Además de evaluación pre-deploy, SICA monitorea hallucinations en producción:

- **Evidence pointer verification:** cada hecho del output apunta a un span del input. Si el span no contiene el hecho, alarma.
- **Confidence calibration:** comparar confidence score declarado vs. tasa real de aceptación por médico. Si están descalibrados, retraining.
- **Out-of-distribution detection:** si un caso es muy distinto a lo visto en entrenamiento (paciente con perfil raro), el sistema debe abstenerse, no inferir.

### 10.6 Stack técnico de evaluación

| Componente | Tecnología | Por qué |
|---|---|---|
| Prompt registry | Langfuse (self-hosted) o solución custom sobre Postgres | Versionado + tracing integrado |
| Eval framework | DSPy + scripts custom | DSPy para optimización declarativa, custom para métricas clínicas |
| Ground truth labeling | Tool interno (Streamlit / Next.js) para 2 médicos en doble ciego | Necesitamos UX clínica, no Label Studio genérico |
| Synthetic patient generation | Construcción manual por médicos + augmentación con LLM bajo supervisión | La calidad importa más que el volumen |
| CI/CD gates | GitHub Actions con scripts custom + Langfuse webhook | Tooling estándar + integraciones |

### 10.7 Operación continua

La AI Evaluation Infrastructure no es un proyecto que termina en R0. Es operación continua:

- **Suite completa corre antes de cada deploy** a producción.
- **Subset rápido corre en cada PR** que toca prompts o modelos.
- **Métricas en producción se monitorean en tiempo real** con alertas si degradan.
- **Médicos del partner revisan trimestralmente** una muestra aleatoria de outputs para validar que el sistema no se está degradando silenciosamente.

---


## 11. Arquitectura técnica

### 11.1 Principios arquitectónicos

1. **El modelo de datos canónico es la pieza central, no el LLM.** FHIR R4 como representación canónica de todo lo clínico.
2. **Multi-modelo con routing explícito.** No depender de un solo proveedor de IA.
3. **PHI sensible nunca sale a cloud sin política explícita.** Default es procesamiento local; escalamiento cloud es decisión deliberada.
4. **Cada output queda auditado.** Versión de modelo + prompt + datos de entrada + timestamp + edición/aceptación del médico.
5. **Embebible, no reemplazante.** UI vive como launch button contextual desde el HIS del partner.

### 11.2 Diagrama de flujo (alto nivel)

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
        Auditoría + feedback + Eval Infrastructure → loops del Flywheel
```

### 11.3 Stack

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

### 11.4 Política de routing de modelos

| Tarea | Modelo default | Fallback / escalamiento | Razón |
|---|---|---|---|
| Resumen de notas, labs, reportes | MedGemma 4B local | Gemini 2.5 Flash si contexto >32k tokens | PHI sensible, latencia importa |
| Extracción estructurada de PDF nativo | Gemini 2.5 Flash | MedGemma 4B local | Gemini tiene visión nativa de PDFs |
| OCR de PDF escaneado | Document AI | Tesseract local | Document AI optimizado para manuscritos |
| Retrieval / búsqueda visual | MedSigLIP embeddings | — | Encoder dedicado, no generación |
| Razonamiento clínico complejo | MedGemma 27B text-only si disponible; Gemini 2.5 Pro si no | — | Profundidad >tarea simple |
| Care gaps / detección de brechas | Reglas + retrieval híbrido + MedGemma 4B | — | Tarea estructurada |
| Cualquier output con baja confianza | **Abstención obligatoria** | El médico decide sin sugerencia | "No encontrado" > "alucinado" |

### 11.5 Costos de cómputo (anclajes técnicos)

`[CITADO — Google Cloud pricing]`

| Opción | Tarifa oficial | Costo aprox. mensual 24/7 | Uso recomendado |
|---|---:|---:|---|
| G2 `g2-standard-4` (1× L4) | USD 0.7068/h | USD 516/mes | Inferencia liviana, embeddings, MVP controlado |
| A2 `a2-highgpu-1g` (1× A100) | USD 3.6734/h | USD 2,682/mes | Inferencia robusta, concurrencia media |
| A3 High `a3-highgpu-8g` (8× H100) | USD 88.49/h | USD 64,698/mes | **No recomendado para bootstrap** |

**Lectura.** El MVP no necesita H100. Diseñar para L4 / A100 puntual.

### 11.6 Modelo de datos: principios FHIR

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

## 12. Validación clínica

### 12.1 Filosofía: riesgo incremental

Marco base: IMDRF (validez científica + desempeño analítico + desempeño clínico) + principios OMS (autonomía humana, transparencia, responsabilidad, beneficio público).

### 12.2 Plan de validación por etapa

| Etapa | Qué se valida | Diseño |
|---|---|---|
| **Retrospectiva** (R0) | Exactitud de resumen, extracción, care gaps, handoff | Benchmark sobre historias desidentificadas + doble revisión clínica |
| **Shadow mode** (R2) | Seguridad operacional y calidad sin impacto en atención | Sistema corre en paralelo, no se muestra al médico o se muestra sin uso mandatorio |
| **Piloto asistivo** (R3, R4) | Aceptación médica y ahorro de tiempo | Médicos aceptan / editan / rechazan cada output |
| **Despliegue controlado** (R5) | Impacto en flujo y calidad | Seguimiento prospectivo de KPIs por servicio |
| **Expansión** (post-18m) | Generalización intersede e interespecialidad | Validación sitio por sitio |

### 12.3 Métricas de validación

| Caso de uso | Métrica primaria | Umbral interno objetivo |
|---|---|---:|
| Resumen longitudinal | Exactitud factual por span / omisiones críticas | >95% en hechos críticos |
| Extracción documental | F1 macro por campo clínico | >0.90 en campos críticos |
| Care gaps | Recall de brechas relevantes | >0.90 |
| Handoff materno-neonatal | Completitud de datos críticos | >95% |
| Brief preanestésico | Completitud + tasa de corrección crítica | <10% correcciones críticas |
| Adopción | Tasa de aceptación / edición ligera | >60% |

### 12.4 Cómo se conecta con Eval Infrastructure

La validación clínica de § 12 y la AI Evaluation Infrastructure de § 10 son la misma cosa vista desde dos ángulos:

- § 10 es la infraestructura técnica permanente (regression tests, prompt registry, synthetic patients).
- § 12 es el proceso clínico formal de validación (retrospectiva, shadow, piloto, validación firmada).

§ 10 produce los números que § 12 valida con médicos.

---

## 13. Marco regulatorio peruano

### 13.1 Tres frentes regulatorios para Fase 1

En orden de prioridad **para SICA**:

1. **Protección de datos personales (Ley 29733)** — el más urgente.
2. **Historia clínica electrónica (RENHICE + SIHCE)** — define cómo nos integramos.
3. **DIGEMID / software como dispositivo médico** — define qué podemos claim-ear.

### 13.2 Protección de datos (Ley 29733 y reglamento)

Obligaciones clave:

- **Consentimiento libre, previo, expreso, inequívoco e informado.** Para datos sensibles (salud), **debe constar por escrito**.
- **Inscripción del banco de datos personales** ante la ANPD.
- **Designación de Oficial de Datos Personales** (DPO).
- **DPIA (evaluación de impacto)** — facultativa pero recomendable.
- **Medidas de seguridad documentadas.**
- **Plazos de respuesta a derechos del titular.**
- **Mensajería no institucional** debe estar formalmente aprobada.

**Acciones para SICA Fase 1:**
- Inscripción de banco de datos antes del primer piloto con datos reales.
- Designación de DPO (fraccional, `[TODO: confirmar con asesor legal si fraccional es defendible en auditoría]`).
- DPIA documentado antes de R1.
- Plantillas de consentimiento clínico revisadas por abogado especializado.

### 13.3 RENHICE y SIHCE

- **Ley 30024 (RENHICE)** + reglamento 2025.
- **Directiva de acreditación SIHCE** aprobada marzo 2025, plazos ampliados 2026.
- **SIHCE requiere firma digital** para ser considerado tal.

**Posicionamiento de SICA:** **"capa copiloto interoperable sobre el SIHCE/EHR existente"**, no "nuevo SIHCE". `[TODO: validar con asesor regulatorio si una capa que escribe datos en el SIHCE del partner queda sujeta a acreditación derivada]`.

### 13.4 DIGEMID y software como dispositivo médico

La definición peruana de dispositivo médico incluye **"aplicativo informático"** cuando el fabricante lo destina a:
- diagnóstico
- prevención
- monitoreo
- tratamiento
- alivio o compensación

**Posición de Fase 1:** claims estrictamente asistivos. Validación clínica antes de ampliar claims. Confirmación obligatoria del médico en cada output.

**`[TODO crítico]`** — la clasificación exacta para un copiloto no autónomo no aparece detallada en una guía pública peruana específica. **Debe validarse con asesor regulatorio local antes de expandir claims hacia "detección de riesgo" en R2-R3.**

### 13.5 Telemedicina

Norma Técnica de Telesalud 2025 existe. **SICA Fase 1 no toca telemedicina.**

### 13.6 Residencia de datos

`[TODO crítico]` — antes de desplegar PHI fuera del país (uso de Gemini cloud) — validar contractual y legalmente.

---

## 14. Go-to-market

### 14.1 ICP (Ideal Customer Profile)

**Clínica privada peruana mediana** con:

- Servicios completos materno-infantiles: ginecología, obstetricia, medicina fetal, pediatría, neonatología, UCIN, centro obstétrico, centro quirúrgico, anestesiología, emergencia gineco-obstétrica 24/7.
- 200–800 partos/año.
- HIS o SIHCE existente (cualquier nivel de madurez).
- Director médico con autonomía operativa de decisión.
- Disposición a pagar piloto, no solo POC gratis.

### 14.2 Motion comercial

| Etapa | Qué vender | A quién | Promesa |
|---|---|---|---|
| Entrada | Piloto pagado 8–12 semanas | Dirección médica + jefe obstetricia/neonatología + TI | Menos tiempo de revisión + mejor handoff |
| Expansión interna | Materno + anestesia + neonatología | Calidad / operaciones | Mejor completitud documental + menos omisiones |
| Expansión de sede | Repetición en otra sede / red | Gerencia corporativa | Estandarización + benchmarking |
| Fase B2C | Companion de alta | Clínica (no consumidor directo) | Extensión de valor B2B ya probado |

### 14.3 Discurso comercial (a director médico)

> **"SICA no reemplaza su HIS. Es una capa de inteligencia clínica que se monta sobre lo que ya tienen, reduce el tiempo de revisión de historia, mejora el handoff entre obstetricia y neonatología, y deja trazabilidad completa para calidad y auditoría."**

### 14.4 Pricing (sugerido, validar con 10-15 entrevistas)

`[ASUMIDO]`

| Plan | Alcance | Precio sugerido |
|---|---|---:|
| Piloto clínico | 1 sede, hasta 10 médicos, 8–12 semanas, 2 workflows | Setup USD 6,000 + USD 1,200/mes |
| Materno-Neo Core | 1 sede, hasta 30 médicos, 5 workflows, analytics básicos | Setup USD 10,000 + USD 2,800/mes |
| Red / Enterprise | Multisede, SSO, SLA, dashboards corporativos | Setup desde USD 20,000 + desde USD 6,500/mes |

### 14.5 Adopción médica real

Reglas operativas:

- Acceso con un clic desde la historia
- Resumen listo **antes** de la consulta / procedimiento
- Output siempre editable
- Evidencia visible (nunca caja negra)
- Sin copy-paste largo
- Shadow mode antes de uso mandatorio
- Champions médicos por especialidad (alimentado por Distribution Engine § 8)
- Comité quincenal de feedback con clínicos + TI

---

## 15. Modelo de negocio y proyecciones

### 15.1 Modelo de negocio

**Clinical workflow SaaS B2B.** Unidad económica: la sede clínica o servicio. Ingresos componentes:
1. Setup de integración (one-time)
2. Licencia mensual SaaS
3. Servicios de adaptación / validación clínica

Etapa posterior: componente B2C white-label (companion de alta) + APIs cobrables (ver Platform Strategy § 17).

### 15.2 Supuestos financieros

`[ASUMIDO — modelo de trabajo, validar con 10-15 entrevistas comerciales]`

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

### 15.3 Proyección a 3 años

`[ASUMIDO]`

| Año | Clientes al cierre | Ingresos | Margen bruto | Opex | EBITDA |
|---|---:|---:|---:|---:|---:|
| 1 | 3 | USD 62,000 | USD 38,000 | USD 170,000 | **-USD 132,000** |
| 2 | 8 | USD 238,000 | USD 167,000 | USD 260,000 | **-USD 93,000** |
| 3 | 18 | USD 655,000 | USD 504,000 | USD 390,000 | **USD 114,000** |

**Cuestionamiento al modelo:** la curva 3→8→18 con ciclo 3-6 meses founder-led implica un ritmo de cierre que rara vez se sostiene sin AE dedicado antes del mes 12. Adelantado en hiring plan a mes 9-10. `[Revisar antes de pitch.]`

### 15.4 Presupuesto 18 meses

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

---

## 16. Expansion Logic post-18m

El roadmap R0-R5 cubre 18 meses. Después de R5, SICA tiene un partner fundador maduro, sede 2 onboarded y caso de uso documentado. La pregunta es: **¿hacia dónde se expande?**

La expansión sigue una **lógica de capas concéntricas**, no de features acumuladas:

### 16.1 Las cinco capas de expansión

```
Capa 1: Wedge (R1-R2)
└─ Resumen obstétrico + checklist prenatal en 1 clínica de Lima

Capa 2: Continuidad clínica vertical (R3-R4)
└─ Handoff materno-neonatal + brief preanestésico (misma clínica)
   └─ Convierte SICA de "feature" a "infraestructura de continuidad"

Capa 3: Longitudinalidad temporal (R5)
└─ Pediatría / CRED + multi-sede
   └─ Cierra el loop madre→neonato→niño 0-5 años

Capa 4: Expansión geográfica LATAM (Mes 18-36)
└─ Chile, Colombia, Ecuador
   └─ Mismos workflows materno-infantiles, distinto regulador

Capa 5: Multi-specialty Clinical Intelligence (Mes 36+)
└─ Misma arquitectura aplicada a otras verticales longitudinales:
   - Cardiología crónica (HTA, IC)
   - Oncología en seguimiento
   - Salud mental con continuidad
```

### 16.2 Por qué este orden específico

**Capa 1 → 2 (vertical antes que horizontal).** Probar continuidad dentro de una clínica antes de replicar a otras. Si SICA no logra que un mismo paciente sea seguido bien entre obstetricia y neonatología en el partner fundador, no tiene caso intentar multi-sede.

**Capa 2 → 3 (madre→bebé antes que multi-clínica).** El loop longitudinal (R5) cierra la tesis fundamental. Sin él, SICA es "varias herramientas en una clínica". Con él, SICA es "memoria longitudinal materno-infantil".

**Capa 3 → 4 (Perú maduro antes que LatAm).** Saltar a Chile/Colombia antes de tener 3+ sedes en Perú dispersa esfuerzo y diluye foco regulatorio. Cada país agrega su propia versión de Ley 29733, su propia DIGEMID. Validar el playbook en Perú primero.

**Capa 4 → 5 (geografía antes que multi-especialidad).** Replicar el wedge materno-infantil en LatAm es un ejercicio de localización. Saltar a oncología o cardiología es construir capability nueva. Lo primero genera ingresos en el playbook conocido; lo segundo es R&D.

### 16.3 Criterios de salida hacia cada capa

| Transición | Criterio mínimo |
|---|---|
| Capa 1 → 2 | R2 cumple gate de salida + champions formados |
| Capa 2 → 3 | R4 con documento de validación clínica firmado |
| Capa 3 → 4 | 3+ sedes peruanas onboarded + playbook documentado |
| Capa 4 → 5 | 2+ países activos + ingresos recurrentes >USD 2M ARR |

### 16.4 Anti-patrones de expansión

Errores que SICA evita deliberadamente:

- **Expansión multi-vertical prematura** — sumar cardiología o oncología antes de R5 cerrado en materno-infantil dispersa equipo y datos.
- **B2C antes de B2B maduro** — el companion para madres requiere infraestructura clínica probada detrás. Construirlo en mes 12 mata foco.
- **Geographic dump** — vender en 5 países a la vez con representantes part-time genera ingresos cosméticos sin moat.
- **Pivot a HIS completo** — la tentación de "ya tenemos los datos, hagamos el sistema" mata el wedge. SICA es capa, no sistema.

---

## 17. Platform Strategy (horizonte año 3+)

Esta sección describe el **destino arquitectónico** de SICA, no la fase actual. Explícitamente: SICA en Fase 1 (mes 0-18) es **producto vertical**, no plataforma. La transición a plataforma ocurre **después de R5 cerrado y con 3+ clínicas en producción**, no antes.

### 17.1 Por qué SICA puede ser plataforma (eventualmente)

Las cinco capacidades de § 6 (Memory Graph, Reasoning Engine, Ingestion Layer, Explainability Layer, Copilot UI) son **componentes reutilizables**. Hoy se exponen a través de la UI clínica del partner. Mañana se exponen como **APIs cobrables a otros operadores del sistema de salud**:

| API potencial | Audiencia | Caso de uso |
|---|---|---|
| **Longitudinal Risk API** | Aseguradoras, empresas de medicina prepagada | Risk scoring materno-infantil para pricing y prevención |
| **Handoff Intelligence API** | Otros HIS / EHR que quieran agregar inteligencia | Embed de handoff inteligente en sus productos |
| **Clinical Summaries API** | Sistemas de gestión hospitalaria | Resumen automático embebido |
| **Maternal Timeline API** | Apps de embarazo B2C que quieran integrar datos clínicos | Acceso autorizado por la madre a su timeline desde apps consumer |
| **Pediatric Continuity API** | Plataformas de telemedicina pediátrica | Acceso a CRED histórico para consultas remotas |

### 17.2 Por qué NO ahora

Tres razones específicas por las que vender platform en Fase 1 sería un error:

1. **Sin producto vertical maduro, las APIs son aspiracionales.** Cobrar por una "Longitudinal Risk API" cuando SICA solo tiene 1 cliente con 6 meses de datos es vender humo.
2. **Distribution Engine de plataforma es distinto al de producto.** Vender APIs a aseguradoras requiere equipo enterprise sales con experiencia BD. Vender producto a clínicas requiere medical champions. Mezclar los dos antes de tiempo dispersa.
3. **La narrativa "somos plataforma" es contraproducente con compradores clínicos.** Un director médico no quiere "plataforma de APIs" — quiere "resumen obstétrico que ahorra 6 minutos por consulta". El framing platform es para inversores, no para clientes iniciales.

### 17.3 Cómo se prepara la transición sin venderla

Aunque platform no es el discurso de Fase 1, la arquitectura técnica desde día uno se diseña pensando en ella:

- **APIs internas con contratos claros** entre Memory Graph, Reasoning Engine, UI. Eventualmente se exponen externamente.
- **Multi-tenancy estricto** desde R5 — sin esto, exponer APIs a terceros es riesgo regulatorio.
- **Versionado de APIs internas** desde día uno — convertirlas en externas será cuestión de auth + rate limiting + documentación.
- **Data residency configurable** — algunos clientes externos podrán requerir que sus datos no se mezclen con SICA core.

### 17.4 Señales de que es momento de pivotar a plataforma

| Señal | Cuándo aparece |
|---|---|
| 3+ clínicas en producción con renovación | Mes 18-24 |
| Inbound de aseguradoras o HIS pidiendo integración | Mes 24+ |
| Volumen de datos longitudinales suficiente para modelos predictivos defendibles | Mes 30+ |
| Equipo de enterprise sales con experiencia BD contratado | Mes 24-30 |

**Hasta que 3 de las 4 señales estén presentes, la respuesta a "¿somos plataforma?" es: "Estamos construyendo la infraestructura que se convertirá en plataforma. Hoy es producto."**

---

## 18. Riesgos y mitigación

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Claims demasiado agresivos | Empujan a régimen DIGEMID antes de tiempo | Mantener claims asistivos + validación obligatoria del médico |
| Falta de integración con HIS del partner | Producto fuera del flujo, baja adopción | Conectores ligeros + launch embebido desde R2 |
| Calidad de PDFs y datos caóticos | Outputs malos | Empezar por extracción + revisión humana + fallback manual |
| Resistencia médica | Bajo uso real | Distribution Engine + shadow mode + champions + evidencia visible + edición fácil |
| Riesgo de privacidad / brecha | Frenazo legal y comercial | DPO + banco de datos inscrito + DPIA + separación de entornos + auditoría |
| Lock-in de proveedor IA | Costo o disrupción | Orquestación multi-modelo + capa de abstracción de modelos |
| Infraestructura sobredimensionada | Burn innecesario | Arquitectura para L4 / A100 puntual, no H100 |
| Falta de dataset local | Mala generalización | Validación retrospectiva con datos del partner antes de R1 |
| **Partner fundador no firma a tiempo** | Roadmap se desplaza 3-6 meses | Negociación paralela con 2-3 prospects desde Mes 0 |
| **MedGemma 4B no alcanza umbral en historias locales** | R0 falla, stack se reconsidera | Plan B definido: 27B text-only o Gemini default para PHI con políticas estrictas |
| **Modelo financiero optimista en conversión piloto→core** | Runway insuficiente Año 2 | Acelerar contratación de AE a mes 9-10, no mes 12 |
| **Categoría "Clinical Intelligence Infrastructure" no resuena en pitch** | Fundraising más difícil | Mantener dual framing: vertical SaaS para inversores conservadores, platform para visionarios |
| **Flywheel no arranca por bajo volumen del partner** | Sin datos, sin moat | Partner con >300 partos/año + uso obligado del shadow mode |
| **Eval Infrastructure subdesarrollada** | Hallucinations en producción no detectadas | Eval suite es bloqueante de R1+, no opcional |
| **Distribution Engine no produce KOLs a tiempo** | Credibilidad clínica baja en Año 2 | KPI explícito: 3 KOLs firmados como advisors antes mes 12 |

---

## 19. Equipo y hiring

### 19.1 Roles fundadores (Día 0)

| Rol | Tipo | Responsabilidad |
|---|---|---|
| CEO / Founder comercial | Full-time | Ventas founder-led, pilotos, fundraising, Distribution Engine |
| CTO / Founder ML | Full-time | Arquitectura, modelos, ingeniería, Eval Infrastructure |
| Líder clínico fundador o advisor | 0.2-0.4 FTE | Validación clínica, credibilidad médica, KOLs, acceso a partners |

### 19.2 Hires por fase

| Momento | Rol | Tipo |
|---|---|---|
| Mes 2-3 | Full-stack / integration engineer | Full-time |
| Mes 4-6 | Clinical informaticist / QA clínico | Part-time o full-time |
| Mes 6-9 | Product designer / customer success inicial | Part-time |
| **Mes 9-10** | **AE / implementation lead** (adelantado) | Full-time |
| Mes 9-12 | Security & compliance counsel | Fractional |
| Mes 12+ | MLOps engineer | Full-time según tracción |

### 19.3 Oficial de Datos Personales

Requerido por norma cuando hay tratamiento de gran volumen o datos sensibles. Puede ser fraccional al inicio, pero `[TODO: validar con asesor legal]`.

### 19.4 Operación AI-native

SICA opera como AI-native company desde día uno. Detalle en `docs/operating-model.md` (placeholder Fase 2). Resumen:

- Producto: specs asistidas por IA, sprint planning con IA, issue generation con IA.
- Ingeniería: Claude Code workflows, AI PR reviews, AI architecture analysis.
- Clínico: AI annotation workflows, AI-assisted validation.
- GTM: AI research, AI CRM enrichment, AI sales prep.

---

## 20. Lo que NO entra en Fase 1

Reafirmación de scope. Ninguno de estos features se construye en los primeros 18 meses:

- Ambient scribe / dictado médico
- Clasificación / retrieval multimodal avanzado de imágenes
- Companion B2C
- Telemedicina / teleconsulta
- Diagnóstico autónomo de cualquier tipo
- Expansión Chile / Colombia / México
- Integración con seguros / pagos
- APIs externas cobrables (Platform Strategy § 17 es horizonte)
- Mobile app nativa (la PWA del panel basta)
- Multi-especialidad fuera de materno-infantil

---

## 21. Pendientes críticos (TODOs)

Cosas que deben resolverse **antes** de pasar a Fase 2 o que bloquean ejecución:

### Críticos (bloqueantes)

- [ ] **Validación regulatoria con asesor DIGEMID local** sobre clasificación de SICA como software asistivo no dispositivo médico.
- [ ] **Validación con asesor legal de protección de datos** sobre: inscripción banco de datos, DPIA, DPO fraccional, plantillas de consentimiento.
- [ ] **Verificación de marca SICA en Indecopi** (riesgo de colisión con SICA – Sistema de Integración Centroamericana).
- [ ] **Confirmación de partner fundador.** Sin partner, R0 no arranca.
- [ ] **Acceso a 150-200 historias obstétricas desidentificadas** para benchmark R0.
- [ ] **Análisis competitivo Perú/LatAm real.** Hipótesis actual: no hay competidor directo. Validar con field research.
- [ ] **Identificación de 5 KOLs target** para Distribution Engine (Sociedad Peruana de Obstetricia y Ginecología, Neonatología, Pediatría).

### Importantes (no bloqueantes, resolver en primeros 90 días)

- [ ] Revisión de licencia del repo (propietaria cerrada vs. abierta).
- [ ] Decisión sobre residencia de datos: ¿toda inferencia local en Perú o se permite cloud regional?
- [ ] Decisión sobre modelado FHIR de relación madre-neonato.
- [ ] Validación de pricing con 10-15 entrevistas comerciales reales.
- [ ] Definición de plan B para R0 si MedGemma 4B no alcanza umbral.
- [ ] Definición de proceso de inscripción de banco de datos personales ante ANPD — timeline.
- [ ] Dato peruano específico de burnout en obstetricia/neonatología para reforzar § 3.6.

### Pendientes para narrativa de fundraising (cuando aplique)

- [ ] TAM / SAM / SOM con números peruanos y de LATAM defendibles (ver `docs/fundraising-narrative.md`).
- [ ] Pitch deck en formato a16z / YC.
- [ ] Cap table inicial.
- [ ] Estructura legal de la empresa (SAC peruana, holding US, otro).
- [ ] Comparación financiera con comparables (Abridge Series A, Nabla, Ambience).

---

**Fin del documento estratégico v0.2.**

Próximo paso: validar con asesor clínico y regulatorio, luego pasar a Fase 2 (construcción de monorepo y capa de ejecución).
