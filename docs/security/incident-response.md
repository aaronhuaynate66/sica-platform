# Plan de respuesta a incidentes

**Versión:** 0.1
**Última actualización:** 2026-05-21
**Audiencia:** Founder, equipo de ingeniería, DPO (cuando exista), partner fundador.
**Estado:** Política operativa. SICA es pre-producto; este plan describe el procedimiento que se aplicará desde el primer incidente posible.

---

## Propósito

Definir el procedimiento que SICA seguirá cuando ocurra un incidente de seguridad, brecha de PHI, compromiso de credenciales, falla técnica con riesgo clínico, u otro evento que requiera respuesta estructurada.

**Principio rector:** velocidad sobre perfección durante el incidente; rigor documental después. El objetivo durante la respuesta es **contener daño + preservar evidencia + cumplir plazos legales**, no escribir el post-mortem perfecto.

---

## 1. Tipos de incidentes

SICA reconoce cinco tipos de incidente. Cada uno tiene severidad y plazos asociados.

| Tipo | Definición | Ejemplos | Severidad típica |
|---|---|---|---|
| **Brecha de PHI** | Acceso, exposición, alteración o pérdida no autorizada de información de salud identificable | Bucket público con PDFs clínicos; query SQL que devuelve datos de otro paciente; export accidental a entorno no autorizado | Crítica |
| **Compromiso de credenciales** | Pérdida o exposición de API keys, llaves de cifrado, credenciales de acceso | API key en commit público; phishing exitoso a operador | Alta o crítica según alcance |
| **Falla técnica con riesgo clínico** | Bug o degradación que produce outputs incorrectos que pueden afectar decisiones médicas | Resumen obstétrico con datos de otra paciente; brief preanestésico con ASA mal calculado | Alta o crítica según uso clínico activo |
| **Downtime / indisponibilidad** | Sistema no responde en momento donde es crítico | Brief preanestésico no disponible durante cesárea de emergencia | Variable según contexto |
| **Incidente regulatorio / contractual** | Violación detectada de política interna o cláusula contractual con partner | Uso de Claude con PHI real; PHI almacenada sin cifrado | Alta |

### 1.1 Clasificación de severidad

| Severidad | Definición | Tiempo máximo a triage |
|---|---|---:|
| **Crítica (S1)** | Brecha confirmada de PHI; sistema afecta decisión clínica activa con error grave; compromiso de credenciales productivas | 30 minutos |
| **Alta (S2)** | Brecha sospechada; bug con potencial clínico no confirmado en producción; compromiso de credenciales no-productivas | 4 horas |
| **Media (S3)** | Vulnerabilidad detectada sin explotación; bug que afecta funcionalidad sin riesgo clínico inmediato | 1 día hábil |
| **Baja (S4)** | Problema cosmético o de baja consecuencia; reporte de scanner sin path de explotación | 1 semana |

---

## 2. Roles

SICA es Fase 1 — founder + asesores + bot. El plan **no asume un comité de seguridad de 10 personas**. Los roles existen como funciones; una sola persona puede cubrir varios mientras el equipo es pequeño.

| Rol | Responsabilidad | Quién hoy | Quién en producción (target) |
|---|---|---|---|
| **Incident Commander (IC)** | Coordina la respuesta. Una sola persona en charge. Toma decisiones, comunica, no ejecuta. | Founder | Founder o líder técnico designado |
| **Investigador técnico** | Diagnóstico, contención técnica, recolección de evidencia | Founder | Ingeniero de seguridad / SRE |
| **Comunicador** | Comunicación interna y externa (partner, ANPD, titulares, prensa si aplica) | Founder + asesor legal | Founder + DPO + asesor legal externo |
| **DPO** | Decisión sobre notificación regulatoria a ANPD y a titulares | `[TBD — DPO no designado aún]` | DPO formal |
| **Asesor legal** | Decisión sobre obligaciones legales, redacción de notificaciones, manejo de responsabilidad | `[TBD — asesor externo a contratar antes del primer dato real]` | Asesor legal externo |
| **Médico de guardia** (cuando aplique riesgo clínico) | Decisión sobre impacto clínico, mitigación inmediata para pacientes | `[TBD]` | Líder clínico del partner |
| **Sponsor en el partner** | Punto de contacto en la organización cliente | `[TBD — definir al cerrar partner fundador]` | Director médico o equivalente |

**Regla operativa:** durante un incidente S1 o S2, el Incident Commander **no escribe código ni ejecuta comandos**. Coordina. La separación de roles previene errores bajo presión.

---

## 3. Matriz de escalamiento

| Severidad | Quién se entera primero | A quién se escala automáticamente | Plazo de escalamiento |
|---|---|---|---:|
| S1 (crítica) | Cualquiera del equipo o detección automática | Founder + DPO + asesor legal + sponsor del partner | Inmediato (<15 min) |
| S2 (alta) | Cualquiera del equipo o detección automática | Founder + DPO | 1 hora |
| S3 (media) | Equipo técnico | Founder en daily | Próximo daily |
| S4 (baja) | Triage normal | — | — |

**Cómo se escala:**

1. **Canal primario:** llamada de voz directa al Incident Commander. Texto/email **no es** canal primario para S1/S2.
2. **Canal secundario:** mensaje en canal de incidentes (Slack/Teams `[TODO — definir herramienta]`).
3. **Canal de respaldo:** SMS a número de guardia `[TODO — establecer cuando exista]`.

---

## 4. Playbook: brecha de PHI sospechada

**Objetivo:** contener, preservar evidencia, evaluar alcance, cumplir notificaciones legales.

### Paso 1 — Detección y triage (0-30 min)

- Quien detecta documenta inmediatamente en un canal seguro (no en chat público): qué se vio, cuándo, dónde, cómo se descubrió.
- Llamar al Incident Commander.
- **No tocar el sistema afectado** todavía — preservar el estado para evidencia.
- IC clasifica severidad inicial (S1 por default si hay sospecha real).

### Paso 2 — Contención inmediata (30 min - 2 h)

- IC autoriza acciones de contención. Posibles:
  - Revocar credenciales potencialmente comprometidas.
  - Bloquear acceso al recurso afectado.
  - Desactivar el workflow o endpoint involucrado.
  - Aislar el sistema afectado de la red.
- **Antes** de cada acción de contención, snapshot del estado actual (logs, configuración, evidencia forense).
- Investigador técnico ejecuta; IC autoriza y registra.

### Paso 3 — Evaluación de alcance (2 - 12 h)

Determinar y documentar:

- **¿Qué datos están afectados?** Categorías y volúmenes aproximados.
- **¿Cuántos titulares están afectados?** Listado o estimación.
- **¿Hubo exfiltración real o sólo acceso?** Logs de red, audit logs.
- **¿Por cuánto tiempo estuvo la exposición activa?** Desde primer evento hasta contención.
- **¿Qué identidades están comprometidas?** Usuarios, servicios, API keys.

Output: documento de evaluación de alcance, firmado por IC y DPO.

### Paso 4 — Notificación legal a ANPD (12 - 72 h)

`[TODO — confirmar plazo legal exacto con asesor; este documento usa 72h como referencia conservadora; el plazo real puede ser más corto o tener formato específico que la ANPD requiere]`.

Si la evaluación de alcance confirma brecha:

- DPO + asesor legal redactan notificación a ANPD.
- Founder firma.
- Envío por canal oficial ANPD.
- **Guardar acuse de recibo** como evidencia.

Contenido típico (sujeto a formato ANPD):
- Descripción de la brecha.
- Categorías y volumen de datos afectados.
- Titulares afectados (número, perfil).
- Consecuencias probables.
- Medidas tomadas o propuestas.
- Punto de contacto.

### Paso 5 — Notificación a titulares afectados

`[TODO — confirmar criterios exactos: la Ley 29733 puede requerir notificación a todos los afectados o sólo si el riesgo es alto]`.

- Plantilla pre-aprobada (preparar antes del primer dato real).
- Canal: el que el partner use para comunicación oficial con pacientes (email, SMS, contacto en consulta).
- Lenguaje: claro, sin minimizar, con instrucciones de acción si aplica.

### Paso 6 — Comunicación al partner

- IC + founder contactan al sponsor del partner por canal acordado.
- Reunión presencial o videocall en <24h del descubrimiento.
- Documentación escrita del incidente y plan de respuesta enviada formalmente.

### Paso 7 — Comunicación interna

- Todo el equipo recibe brief escrito en <24h del descubrimiento.
- No detalles forenses en canal abierto — sólo lo necesario para coordinar.
- Recordatorio de política de no compartir externamente sin autorización del IC.

### Paso 8 — Comunicación externa (prensa / redes)

- **Sólo si pregunta llega.** SICA no proactivamente publica en redes durante un incidente.
- Plantilla de respuesta a prensa pre-aprobada por asesor legal.
- Vocero único: founder.

### Paso 9 — Resolución técnica

- Investigador técnico ejecuta remediación.
- Tests de regresión específicos para el vector explotado.
- Validación independiente por otro ingeniero o asesor.

### Paso 10 — Post-mortem (en <14 días del cierre)

Ver sección 7.

---

## 5. Comunicación

### 5.1 Interna

- **Durante el incidente:** canal cerrado, sólo equipo de respuesta.
- **Post-contención:** brief al resto del equipo en <24h.
- **Post-mortem:** compartido con todo el equipo + asesores + partner cuando aplique.

### 5.2 Externa — Partner

- Sponsor del partner notificado en <24h del descubrimiento (S1/S2).
- Reuniones diarias durante respuesta activa.
- Reporte final firmado.

### 5.3 Externa — ANPD (Ley 29733)

- Notificación dentro del plazo legal `[TODO — confirmar]`.
- Formato según requerimiento ANPD vigente.
- Punto de contacto: DPO o founder en su defecto.

### 5.4 Externa — Titulares afectados

- Sólo cuando la evaluación legal lo determine.
- Plantilla pre-aprobada.
- Canal coordinado con el partner.

### 5.5 Externa — Prensa / público general

- Sólo reactiva. No proactiva.
- Vocero único.
- Lenguaje aprobado por asesor legal.

---

## 6. Plazos legales y operativos

| Acción | Plazo | Fuente |
|---|---:|---|
| Triage inicial S1 | 30 min | Política interna |
| Triage inicial S2 | 4 h | Política interna |
| Notificación a partner (S1/S2) | 24 h | Política interna + contrato |
| Notificación a ANPD | `[TODO — confirmar]` (referencia conservadora: 72h desde conocimiento) | Ley 29733 y reglamento |
| Notificación a titulares afectados | "Sin dilaciones indebidas" | Ley 29733 |
| Resolución técnica | Tan rápido como sea posible, prioridad sobre roadmap | Política interna |
| Post-mortem completo | <14 días desde cierre del incidente | Política interna |

---

## 7. Post-mortem

Cada incidente S1, S2, y cualquier S3 que el IC determine genera un post-mortem **escrito y firmado** dentro de los 14 días posteriores al cierre.

### 7.1 Principio

Blameless. El objetivo es entender qué falló en el sistema (técnico, procesal, comunicacional), no buscar culpables individuales. Una cultura que castiga errores produce reportes incompletos y respuesta más lenta en el siguiente incidente.

### 7.2 Template

```markdown
# Post-mortem — [Identificador del incidente]

**Fecha del incidente:** YYYY-MM-DD
**Severidad:** S1 / S2 / S3
**Duración total:** HH:MM (detección → contención → resolución)
**Datos afectados:** [Categoría, volumen aproximado]
**Titulares afectados:** [Número o "N/A"]
**Incident Commander:** [Nombre]
**Autor del post-mortem:** [Nombre]
**Firmado por:** Founder + DPO

## Resumen ejecutivo

Tres a cinco frases: qué pasó, qué se hizo, qué impacto, qué se aprendió.

## Línea de tiempo

| Hora | Evento | Actor |
|---|---|---|
| HH:MM | Evento que causó el incidente | — |
| HH:MM | Primera detección | [Quién] |
| HH:MM | Escalamiento al IC | [Quién] |
| ... | ... | ... |
| HH:MM | Contención completa | [Quién] |
| HH:MM | Resolución | [Quién] |

## Causa raíz

Análisis técnico/procesal de qué falló. No "fulano cometió un error" sino "el sistema permitió que el error pasara".

## Impacto

- Técnico
- Clínico (si aplica)
- Regulatorio
- Comercial / reputacional
- Equipo (carga de respuesta)

## Lo que funcionó bien

Sí, esta sección existe. Identificar qué procesos / herramientas / decisiones aceleraron la respuesta.

## Lo que no funcionó

Qué retrasó la detección, contención o resolución. Sin nombres individuales.

## Acciones correctivas

| # | Acción | Owner | Deadline | Status |
|---|---|---|---|---|
| 1 | ... | ... | ... | Pendiente / En progreso / Cerrado |

## Notificaciones realizadas

- [ ] Partner notificado
- [ ] ANPD notificada (si aplica)
- [ ] Titulares notificados (si aplica)
- [ ] Equipo informado
- [ ] Auditor externo informado (si aplica)

## Anexos

- Logs relevantes (sanitizados de PHI)
- Comunicaciones formales
- Decisiones de IC durante el incidente
```

### 7.3 Seguimiento

- Las acciones correctivas se trackean como issues en GitHub con label `incident-followup`.
- El IC verifica cierre de cada acción correctiva.
- Auditoría trimestral de acciones correctivas pendientes.

---

## 8. Ensayo del plan

`[TODO]` — Antes del primer dato real, ejecutar al menos un **table-top exercise**:

- Escenario hipotético (ejemplo: "alguien subió PHI a un repo público por error").
- Equipo simula respuesta sin tocar sistemas reales.
- Mide tiempo a cada hito.
- Documenta gaps detectados.

Frecuencia objetivo: 2 ensayos por año mientras SICA esté en producción.

---

## Referencias

- `STRATEGY.md` § 13.2 — Ley 29733 y reglamento.
- `STRATEGY.md` § 18 — Riesgos y mitigación.
- `docs/security/data-handling.md` — Política de manejo de PHI.
- `docs/security/ley-29733-compliance.md` — Mapeo regulatorio.
- `docs/security/threat-model.md` — Vectores de ataque.
- `docs/decisions/0003-security-and-phi-policy.md` — ADR que adopta este plan.
- Referencias generales: NIST SP 800-61 (Computer Security Incident Handling Guide), ENISA Incident Response, Google SRE Book — capítulo Postmortem Culture.
