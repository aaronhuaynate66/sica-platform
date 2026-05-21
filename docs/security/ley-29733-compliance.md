# Cumplimiento Ley 29733 — mapeo a SICA

**Versión:** 0.1
**Última actualización:** 2026-05-21
**Audiencia:** Founder, asesor legal de protección de datos peruano, asesor regulatorio, auditores.
**Estado:** Borrador interno. SICA es pre-producto; este documento describe **estado actual** y **obligaciones pendientes** antes de procesar PHI real.

---

## Propósito

Mapear cada obligación relevante de la **Ley 29733 (Protección de Datos Personales del Perú)** y su reglamento al estado actual de SICA, identificando brechas, owners y acciones bloqueantes.

Este documento es **vivo**: se actualiza cuando cambia el estado de cumplimiento de cualquier obligación. La firma del asesor legal externo es requisito para cambiar el estado de cualquier fila de "Pendiente" a "Cumplido" salvo evidencia documental adjunta.

**Aviso importante.** Este documento no es asesoría legal. Los plazos, requisitos y obligaciones citados son interpretación de trabajo del equipo de SICA basada en STRATEGY § 13 y lectura general de la Ley 29733. **Todos los puntos críticos requieren validación por asesor legal peruano externo antes de tratarse como definitivos.** Donde la interpretación de SICA podría diferir del criterio legal real, aparece `[TODO — asesor legal]`.

---

## Tabla de obligaciones

Estado posibles: `No cumplido` (no se ha iniciado), `En progreso` (iniciado pero incompleto), `Cumplido` (verificado), `No aplica` (con justificación), `Bloqueante` (impide tocar PHI real).

| Obligación legal | Aplica a SICA | Estado actual | Acción requerida | Owner | Deadline |
|---|---|---|---|---|---|
| **Consentimiento libre, previo, expreso, inequívoco, informado, escrito** para tratamiento de datos sensibles de salud | Sí — SICA procesa datos de salud, categoría sensible | No cumplido | Diseñar plantilla de consentimiento aprobada por asesor legal; integrarla en el flujo del partner antes del primer dato real | Founder + asesor legal | Antes de R1 (Mes 5) |
| **Inscripción del banco de datos personales** ante la ANPD | Sí — SICA almacenará bancos de datos de salud | No cumplido — **Bloqueante** | Iniciar trámite de inscripción ante ANPD; mantener documentación lista para auditoría | Founder + asesor legal | Antes del primer PDF real (R0, Mes 0-2) |
| **Designación de Oficial de Datos Personales (DPO)** | Sí — tratamiento masivo de datos sensibles lo requiere | No cumplido — **Bloqueante** | Designar DPO (fraccional permitido si defendible — `[TODO — confirmar con asesor legal]`); registrar designación | Founder | Antes del primer dato real |
| **Evaluación de Impacto en Protección de Datos (DPIA)** | Sí — operación de alto riesgo (datos sensibles, perfilado clínico, IA) | No cumplido | Ejecutar DPIA siguiendo metodología ANPD; documentar mitigaciones; firmar | DPO + founder | Antes de R1 (Mes 5) |
| **Política de retención** documentada y aplicada | Sí | En progreso — política documentada en `data-handling.md`, sin verificación legal | Revisar política con asesor legal; firmar | Founder + asesor legal | Antes de R1 |
| **Derechos del titular**: acceso, rectificación, supresión, oposición, portabilidad | Sí — pacientes del partner son titulares | No cumplido | Diseñar procedimiento operativo (PR técnico + documental) para atender solicitudes; coordinar con partner quién recibe la solicitud | Founder + partner | Antes de R2 (Mes 8) |
| **Plazos de respuesta a derechos del titular** | Sí | No cumplido | Documentar y publicar plazos. `[TODO — confirmar plazo exacto con asesor legal]` | Founder + asesor legal | Antes de R2 |
| **Notificación de brechas a ANPD en plazo legal** | Sí | No cumplido | Documentar en `incident-response.md`; ejecutar simulacro de incidente. `[TODO — confirmar plazo exacto (72h es referencia GDPR, validar 29733)]` | Founder + DPO + asesor legal | Antes del primer dato real |
| **Notificación de brechas a titulares afectados** | Sí | No cumplido | Documentar canal y plantilla de notificación; coordinar con partner | Founder + partner | Antes del primer dato real |
| **Encargados de tratamiento (procesadores externos)** documentados con DPA / contrato | Sí — Google Cloud, Anthropic, otros proveedores | No cumplido | Inventariar todos los terceros; firmar DPA con cada uno antes de exposición a PHI; mantener registro de subprocesadores | Founder + legal | Continuo, primera ronda antes del primer dato real |
| **Transferencias internacionales de datos** | Sí — modelos cloud en regiones US/EU según routing | En progreso — políticas internas documentadas; sin validación legal | Validar con asesor si la base legal (consentimiento, garantías adecuadas, etc.) es suficiente; documentar | Asesor legal | Antes de R1 |
| **Mensajería no institucional (WhatsApp informal con PHI)** prohibida o formalmente aprobada | Sí — relevante para comunicación con partner / pacientes | No cumplido | Política explícita: WhatsApp/email personal **no se usan** para PHI; cualquier excepción requiere consentimiento documentado | Founder | Antes del primer dato real |
| **Registros de actividades de tratamiento** | Sí | En progreso — `data-handling.md` lista categorías y propósitos; pendiente formato ANPD si aplica | Verificar si la ANPD exige formato específico; ajustar | Asesor legal | Antes de R1 |
| **Medidas técnicas y organizativas de seguridad** documentadas | Sí | Cumplido parcialmente — `data-handling.md`, `threat-model.md`, `incident-response.md` cubren la parte técnica. Falta validación legal y firma | Revisión externa | Asesor legal + auditor seguridad | Antes de R1 |
| **Cláusula contractual con el partner (responsable/encargado del tratamiento)** | Sí — definir si SICA es responsable o encargado, o ambos según workflow | No cumplido | Negociar y firmar DPA con partner fundador antes del primer dato real | Founder + partner + legal | Antes del primer PDF real |
| **Consentimiento para uso secundario** (evaluación, fine-tuning) | Sí — uso de datos para mejorar modelo va más allá del tratamiento clínico primario | No cumplido | Diseñar consentimiento explícito para uso secundario; permitir opt-out granular | Founder + asesor legal + ética | Antes de R1 si se planea entrenar con datos del partner |

---

## Detalle por obligación

### Consentimiento informado para datos de salud

La Ley 29733 clasifica los datos de salud como **sensibles** y exige consentimiento que sea simultáneamente **libre, previo, expreso, inequívoco, informado y constar por escrito**. Coherente con STRATEGY § 13.2.

**Qué hace SICA hoy:** nada. No hay sistema desplegado.

**Qué requiere hacer:**
- Plantilla de consentimiento clínico revisada por abogado especializado en datos personales y derecho médico.
- Plantilla diferenciada por: (a) tratamiento clínico primario, (b) uso secundario para evaluación y fine-tuning, (c) investigación si aplica.
- Implementación operativa en el flujo del partner (idealmente en el momento de firma de admisión o consulta).

**Quién es responsable:** founder negocia con partner; asesor legal firma la plantilla.

**Bloqueante para:** primer PDF real en R0.

---

### Inscripción del banco de datos ante ANPD

La ANPD (Autoridad Nacional de Protección de Datos Personales del MINJUS) mantiene un registro nacional de bancos de datos personales. Las organizaciones que tratan datos personales deben inscribir sus bancos.

**Qué hace SICA hoy:** nada.

**Qué requiere hacer:**
- Determinar qué banco(s) inscribir (probable: "Datos clínicos materno-infantiles para asistencia clínica con IA").
- Preparar la declaración: finalidades, categorías de datos, destinatarios, medidas de seguridad, plazos de conservación, transferencias internacionales.
- Presentar trámite por la plataforma ANPD.
- Mantener registro actualizado cuando cambien las características.

**Quién es responsable:** founder ejecuta; asesor legal supervisa.

**Bloqueante para:** primer PDF real. El issue #15 lista "Inscripción del banco de datos personales **iniciada** ante la ANPD (no necesariamente cerrada, pero el trámite empezó)".

`[TODO]` — Plazo real de procesamiento ANPD desde solicitud hasta resolución. Si toma >60 días, planificar inicio del trámite ya.

---

### Designación de DPO

La normativa peruana requiere designación de un Oficial de Datos Personales cuando hay tratamiento de gran volumen o datos sensibles. SICA cumple ambos criterios.

**Qué hace SICA hoy:** nada formal. El founder ejerce funciones de facto.

**Qué requiere hacer:**
- Decisión: DPO interno full-time, interno fraccional, o externo fraccional (servicios de DPO-as-a-service).
- Si fraccional: `[TODO — confirmar con asesor legal si fraccional es defendible en auditoría ANPD]`. STRATEGY § 19.3 ya marca este TODO.
- Registrar designación formal ante ANPD si aplica.
- Documentar funciones, responsabilidades, independencia del DPO.

**Quién es responsable:** founder decide; asesor legal valida estructura.

**Bloqueante para:** primer dato real.

---

### DPIA (Evaluación de Impacto en Protección de Datos)

STRATEGY § 13.2 marca DPIA como **facultativa pero recomendable**. Para SICA — operación de alto riesgo (datos sensibles de salud + IA + perfilado clínico + transferencias internacionales puntuales) — **se trata como obligatoria de facto**.

**Qué hace SICA hoy:** nada formal.

**Qué requiere hacer:**
- Ejecutar DPIA siguiendo metodología reconocida (ANPD, CNIL, ICO como referencias).
- Identificar riesgos específicos: reidentificación, sesgo del modelo, alucinaciones con consecuencia clínica, fuga de PHI, escalamiento cloud no autorizado.
- Documentar mitigaciones (las que están en `data-handling.md` + `threat-model.md`).
- Firmar y archivar; revisar cada 12 meses o ante cambio mayor.

**Quién es responsable:** DPO ejecuta con founder; asesor legal valida.

**Deadline:** Antes de R1 (Mes 5).

---

### Encargados de tratamiento y transferencias internacionales

SICA usa servicios cloud (Google Cloud, Anthropic, potencialmente Document AI) que procesan datos. Cada uno es **encargado de tratamiento** y requiere DPA (Data Processing Agreement).

**Inventario inicial de encargados:**

| Proveedor | Servicio | Datos que procesa | DPA |
|---|---|---|:---:|
| Google Cloud (Vertex AI, Cloud Storage, Cloud KMS) | Cómputo, almacenamiento, gestión de llaves | PHI (con condiciones de § 7 de `data-handling.md`) | `[TODO]` Firmar DPA en términos GCP estándar antes de R0 |
| Anthropic | API Claude (sólo asistencia al desarrollo, no runtime clínico en Fase 1) | Datos sintéticos / desidentificados de desarrollo | `[TODO]` Revisar términos vigentes |
| Document AI (Google) | OCR de PDFs escaneados | PHI con consentimiento + DPA + región controlada | `[TODO]` |
| GitHub | Hosting de código + docs (sin PHI por política) | Configuración y código únicamente; **PHI prohibida** | DPA estándar GitHub Enterprise |
| Proveedor de email corporativo `[TODO]` | Comunicación interna | No PHI por política | DPA estándar |
| `[TODO]` Otros proveedores que aparezcan | — | — | — |

**Transferencias internacionales** — STRATEGY § 13.6 marca `[TODO crítico]`. Antes de R1 hay que validar:

- Si la base legal (consentimiento del titular + garantías contractuales) es suficiente bajo Ley 29733.
- Si la ANPD requiere notificación específica de la transferencia.
- Si hay configuraciones de región que cumplan "residencia de datos en Perú" si el partner lo exige.

---

### Brechas de seguridad — notificación

Coherente con `incident-response.md`. La Ley 29733 y su reglamento requieren notificación a ANPD y a titulares afectados en caso de brecha.

**Plazo de notificación a ANPD:** `[TODO — confirmar exactamente con asesor legal; el documento usa 72h como referencia conservadora alineada con GDPR, pero el plazo peruano puede diferir]`.

**Plazo de notificación a titulares:** "sin dilaciones indebidas" — interpretación pendiente con asesor.

---

### Uso secundario de datos (para evaluación y fine-tuning)

STRATEGY § 9 (Data Flywheel) y § 10 (AI Evaluation Infrastructure) describen uso de datos del partner para mejorar SICA. Esto va **más allá del tratamiento clínico primario** y requiere consentimiento separado.

**Riesgo si no se documenta:** todo el flywheel se vuelve éticamente y legalmente cuestionable.

**Qué requiere hacer:**
- Consentimiento explícito para uso secundario, con opt-out granular.
- Procesamiento sobre datos desidentificados siempre que sea posible.
- Documentación de qué datos se usan y para qué.
- Revisión periódica por comité de ética si el volumen lo justifica.

---

## Bloqueantes para tocar PHI real

Lista numerada de las **acciones que SI O SI** deben estar antes de procesar el primer dato real con el partner fundador. Si alguna no está, el procesamiento no inicia.

1. **DPA firmado con el partner fundador** definiendo responsabilidades de responsable / encargado del tratamiento.
2. **Inscripción del banco de datos personales ante ANPD iniciada** (trámite presentado, número de expediente recibido).
3. **DPO designado** formalmente (puede ser fraccional, pero la designación existe y la persona puede ejercer).
4. **Plantilla de consentimiento informado** revisada por asesor legal externo y operativa en el flujo del partner.
5. **Política de seguridad y manejo de PHI** (este documento + `data-handling.md` + `incident-response.md` + `threat-model.md`) **revisada y firmada** por asesor regulatorio externo.

Adicionalmente, condiciones técnicas (no documentales) que deben verificarse antes del primer PDF real:

6. **Encryption at rest verificada** en object storage donde se almacenarán los PDFs.
7. **MFA enforced** para cualquier identidad con acceso a entornos con PHI.
8. **Audit log activo** capturando cada acceso a recursos clínicos.
9. **Test de tracking funcional**: una operación de prueba aparece correctamente en el audit log.
10. **Plan de respuesta a incidentes ensayado** al menos una vez (table-top exercise).

`[TODO]` — Validar si esta lista de 10 es la mínima necesaria con asesor regulatorio. Puede agregar/quitar elementos.

---

## Referencias

- **Ley 29733** — Ley de Protección de Datos Personales del Perú. Texto vigente.
- **Reglamento de la Ley 29733** — Decreto Supremo y modificaciones.
- **ANPD** (Autoridad Nacional de Protección de Datos Personales) — MINJUS.
- `STRATEGY.md` § 13 — Marco regulatorio peruano.
- `STRATEGY.md` § 19.3 — DPO fraccional como TODO.
- `STRATEGY.md` § 21 — Pendientes críticos.
- `docs/security/data-handling.md` — Política operativa de manejo de PHI.
- `docs/security/incident-response.md` — Plan de respuesta a incidentes.
- `docs/security/threat-model.md` — Modelo de amenazas.
- `docs/decisions/0003-security-and-phi-policy.md` — ADR que adopta este conjunto de políticas.
