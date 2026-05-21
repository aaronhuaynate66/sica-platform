# Roadmap de Producto — SICA

**Versión 0.1 — Fase 1**
**Horizonte:** 18 meses (Mes 0 → Mes 18)

Este documento detalla el roadmap R0–R5 referenciado en `STRATEGY.md` § 5.

---

## Principios del roadmap

1. **Cada release pasa un gate clínico/técnico antes de pasar al siguiente.** No avanzamos a un nuevo caso de uso si el anterior no cumplió métricas de salida.
2. **El primer release no es un feature, es un benchmark.** Sin números de calidad medidos sobre historias locales reales, no se construye UI clínica.
3. **Shadow mode es la barrera natural entre alpha y beta.** Nada se muestra al médico en flujo real hasta que pasó shadow. Nada se vuelve mandatorio hasta que pasó piloto asistivo medido.
4. **Cada release deja audit trail.** Versión de modelo, prompt, datos de entrada, output, edición del médico. Esto es activo regulatorio.

---

## Vista comprimida

| Release | Mes | Wedge | Gate de salida |
|---|---|---|---|
| R0 Foundation | 0–2 | Benchmark + stack mínimo, sin UI clínica | MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas |
| R1 Resumen Obstétrico (Alpha) | 2–5 | Panel standalone, sesiones de revisión | >70% resúmenes útiles sin edición mayor |
| R2 Shadow + Checklist | 5–8 | Embed en HIS, sin uso mandatorio | ≥40% uso + recall brechas ≥80% + 0 incidentes seguridad |
| R3 Handoff Materno-Neonatal | 8–11 | Primer flujo crítico (asistivo) | Completitud ≥95% + correcciones <10% + aprobación neo |
| R4 Brief Preanestésico | 11–14 | Cesárea programada y urgencia | <10% correcciones críticas + aprobación calidad |
| R5 CRED + Multi-sede | 14–18 | Pediatría longitudinal + producto replicable | Sede 2 onboarded + renovación partner |

---

## R0 — Foundation (Mes 0–2)

**Tema:** _"Podemos confiar en lo que mide el modelo antes de pedirle que produzca."_

### Entregables

| Componente | Detalle |
|---|---|
| Dataset de validación | 150–200 historias obstétricas desidentificadas del partner, anonimización auditable |
| Ground truth | Resúmenes + problemas activos + handoffs creados por 2 médicos en doble ciego sobre 50 casos |
| Benchmark harness | Pipeline reproducible: input → output modelo → métrica vs. ground truth |
| Stack mínimo | Postgres + pgvector, ingesta PDF, llamada a MedGemma local + Gemini, sin UI clínica |
| Métricas calibradas | Exactitud factual por span, omisiones críticas, F1 extracción por campo |

### Gate R0 → R1

MedGemma 4B alcanza ≥85% exactitud factual y ≤5% omisiones críticas en resumen obstétrico.

**Si no se cumple:** ruta alternativa explícita — MedGemma 27B text-only, o Gemini default para PHI con políticas estrictas, o fine-tuning ligero sobre dataset local. **No se avanza a R1 sin esta decisión documentada.**

### Riesgos R0

- **Partner no firma acceso a datos a tiempo** → R0 se extiende a 3 meses, todo el roadmap se desplaza.
- **Datos del partner muy heterogéneos / mal estructurados** → la fase de normalización consume el budget de modelado. Mitigación: presupuesto explícito de 30% para data cleaning.

---

## R1 — Resumen Longitudinal Obstétrico, Alpha (Mes 2–5)

**Tema:** _"Un médico puede ver el resumen, pero no lo usa todavía en consulta real."_

### Entregables

| Componente | Detalle |
|---|---|
| Resumen obstétrico | Timeline editable, problemas activos, EG/FUM/FPP reconciliados, evidencia trazable por span |
| Ingesta documental | Conector lectura desde HIS del partner (HL7v2 / FHIR / CSV / PDFs) |
| Normalización FHIR | Subset mínimo: Patient, Encounter, Observation, Condition, DiagnosticReport |
| UI alpha | Panel web standalone (no embebido aún), acceso solo a médicos del piloto |
| Explainability | Cada hecho del resumen muestra documento fuente + timestamp + nivel de confianza |
| Logging clínico | Todo output queda registrado con versión de modelo, prompt y datos de entrada |

### Gate R1 → R2

≥5 obstetras del partner usan el resumen sobre historias reales en sesiones de revisión (no consulta real todavía). >70% de los resúmenes calificados como "útiles sin edición mayor" por feedback estructurado firmado.

**Si no se cumple:** iteración dentro de R1, no avance a R2.

---

## R2 — Shadow Mode + Checklist Prenatal (Mes 5–8)

**Tema:** _"El sistema corre en paralelo a la consulta sin alterarla, y empieza a detectar."_

### Entregables

| Componente | Detalle |
|---|---|
| Embed en HIS | Launch button contextual desde la historia del paciente, dentro del HIS del partner |
| Modo shadow | Resumen se genera automáticamente pre-consulta pero NO es mandatorio |
| Checklist prenatal | Detección de brechas del paquete prenatal según protocolo interno del partner |
| Care gaps engine | Reglas + retrieval híbrido sobre protocolos internos cargados como corpus |
| Tablero clínico | KPIs por médico: uso, tiempo ahorrado estimado, tasa de edición |
| Feedback loop | Botón inline aceptar/editar/rechazar con razón estructurada |

### Gate R2 → R3

3 meses de shadow con ≥15 médicos activos. Resumen usado en ≥40% de consultas obstétricas. Recall de brechas ≥80% sobre ground truth retrospectivo. **Cero incidentes de seguridad de datos.**

### Decisión a tomar en R2

¿La detección de brechas implica claim de "monitoreo" en términos DIGEMID? **Validar con asesor regulatorio antes de salir de shadow a asistivo en R3.**

---

## R3 — Handoff Materno-Neonatal, Piloto Asistivo (Mes 8–11)

**Tema:** _"Primer caso de uso donde el output entra al flujo crítico de atención."_

### Entregables

| Componente | Detalle |
|---|---|
| Handoff automático | Resumen materno relevante generado al momento del parto, disponible en recepción neonatal / UCIN |
| Campos críticos | RPM, fiebre intraparto, GBS, diabetes gestacional, antibióticos intraparto, líquido meconial, Apgar, peso al nacer |
| UI neonatal | Vista específica para neonatólogo / pediatra de UCIN, optimizada para revisión <60 segundos |
| Validación bidireccional | Neonatólogo confirma recepción y marca campos faltantes; feedback al sistema obstétrico |
| Modo asistivo (ya no shadow) | El handoff es parte del workflow, pero edición y confirmación obligatoria |
| Audit reforzado | Cada handoff queda trazado de extremo a extremo: input materno → output → revisión neo |

### Gate R3 → R4

Completitud de campos críticos ≥95% en 30 handoffs consecutivos. Tasa de corrección crítica por neonatólogo <10%. Aceptación formal documentada por jefatura de neonatología.

### Por qué R3 antes que R4

- Handoff pasa **información**, no decide tratamiento → riesgo legal menor.
- ROI más visible para dirección médica (reduce omisiones documentadas).
- Genera el primer "caso vendible" para sede 2.

---

## R4 — Brief Preanestésico Obstétrico (Mes 11–14)

**Tema:** _"Caso de uso de mayor valor por evento y mayor escrutinio clínico."_

### Entregables

| Componente | Detalle |
|---|---|
| Brief preanestésico | Generado al programar cesárea o ante solicitud de emergencia |
| Datos críticos | Alergias, comorbilidades, labs recientes, antecedente anestésico, vía aérea, ASA tentativo |
| Modo urgencia | Versión <30 segundos para cesárea de emergencia obstétrica |
| Integración con quirófano | Print/PDF + vista móvil para anestesiólogo de guardia |
| Doble confirmación | Anestesiólogo firma electrónicamente el brief antes de usarlo |
| Auditoría reforzada | Cada brief con trazabilidad completa, accesible a calidad e indemnidad |

### Gate R4 → R5

<10% de correcciones críticas por anestesiólogo en 50 briefs. Aprobación formal del jefe de anestesiología y comité de calidad del partner. **Documento de validación clínica firmado** — insumo para vender a sede 2.

### Por qué R4 después de R3

- Brief preanestésico toca decisión farmacológica → consecuencias de error más visibles.
- Llegar después de R3 significa que el modelo, el feedback loop y la cultura de uso están maduros.
- El "documento de validación clínica firmado" en este punto es el activo más vendible para fundraising y sede 2.

---

## R5 — Pediatría / CRED + Multi-Sede (Mes 14–18)

**Tema:** _"El producto se vuelve replicable fuera del partner fundador."_

### Entregables

| Componente | Detalle |
|---|---|
| Módulo CRED | Seguimiento de controles, vacunas, anemia, desarrollo, brechas, educación entregada |
| Continuidad madre→bebé | El bebé hereda contexto del handoff R3 y se sigue por pediatría |
| Analytics de calidad | Dashboards para dirección médica: cumplimiento, brechas cerradas, tiempo ahorrado por servicio |
| Implementation playbook | Documentación + scripts para onboarding de sede 2 en <8 semanas |
| Configurabilidad por sede | Protocolos internos editables, no hardcoded |
| Multi-tenancy + SSO | Aislamiento de datos por institución, login federado |
| Audit pack | Reportes de auditoría exportables (Ley 29733, RENHICE) |

### Gate R5 → Expansión

- Sede 2 firmada y onboarded antes del mes 18.
- Renovación del partner fundador en plan Materno-Neo Core.
- Caso de uso documentado en formato vendible (formato pitch / case study).

### Por qué CRED al final

Depende de continuidad longitudinal (meses de seguimiento del mismo bebé). Antes de tener R3 entregando contexto materno al bebé, CRED sería un feature huérfano sin datos para ejercitar.

---

## Vista de KPIs por dimensión

`[ASUMIDO — metas del deep research §4, validar contra línea base local en R1]`

| Dimensión | KPI | Meta piloto 90 días | Meta 12 meses |
|---|---|---:|---:|
| Utilidad clínica | % consultas con resumen usado | 40% | 70% |
| Eficiencia | Reducción tiempo revisión historia | 20% | 35% |
| Documentación | Reducción tiempo armado nota/brief | 25% | 40% |
| Calidad | % brechas relevantes detectadas y aceptadas | 50% | 70% |
| Handoff | Reducción campos críticos omitidos | 30% | 60% |
| Prenatal | Completitud paquete prenatal interno | +10 pts | +20 pts |
| Pediatría | Cierre brechas CRED/anemia/vacunas | +5 pts | +12 pts |
| Adopción | WAU/MAU médico | 0.5 | 0.7 |
| Confianza | Tasa edición/corrección | <35% | <20% |
| Seguridad | Incidentes acceso no autorizado | 0 | 0 |

---

## Decisiones revisables del roadmap

Tres decisiones del roadmap que no son finales — se revisan según contexto del partner fundador:

1. **¿R3 (handoff neonatal) antes que R4 (brief anestésico), o al revés?** Si el partner fundador tiene volumen de cesárea programada significativamente mayor a volumen de UCIN, R4 podría ir primero.
2. **¿R0 dura 2 meses o 3?** Si el partner aún no firmó acceso a datos al inicio, R0 se extiende a 3 meses y todo el roadmap se desplaza.
3. **¿CRED en R5 o se posterga a post-18m?** Si la sede 2 prioriza otro módulo (analytics de calidad, expansión a anestesia adulto), CRED puede correrse.

---

**Gantt visual (mermaid) — pendiente para v0.2 del documento.** Por ahora la tabla comprimida arriba es suficiente.
