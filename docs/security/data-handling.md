# Manejo de datos y PHI — política operativa

**Versión:** 0.1
**Última actualización:** 2026-05-21
**Audiencia:** Equipo de ingeniería, líder clínico, asesor regulatorio, auditores externos.
**Estado:** Política normativa. SICA es pre-producto; estas reglas se aplican desde el primer contacto con datos reales del partner fundador.

---

## 1. Principios fundamentales

Cinco principios no negociables. Cualquier excepción requiere ADR explícito y firma del founder.

1. **PHI nunca sale del entorno controlado del cliente (o de SICA actuando como encargado) sin política explícita y documentada.** El default operativo es procesamiento local; cualquier desviación es decisión deliberada por workflow, no por conveniencia técnica.
2. **El default para inferencia sobre PHI es procesamiento local (MedGemma 4B o 27B según hardware).** Cloud genérico no es default. Coherente con STRATEGY § 11.1 (principio 3) y § 11.4.
3. **Escalamiento a cloud (Gemini, Claude, Document AI) es decisión deliberada por workflow, no default.** Cada workflow que escala a cloud documenta: qué dato sale, por qué no se puede procesar local, qué política aplica, qué auditoría queda.
4. **Cada operación con PHI queda auditada.** Versión de modelo + prompt + hash de input + timestamp + identidad del usuario + edición/aceptación del médico. Sin audit log, no hay operación.
5. **Abstención sobre alucinación.** Cuando no hay evidencia suficiente o el sistema opera fuera de distribución conocida, el output correcto es "no encontrado", no una inferencia generada. Coherente con STRATEGY § 11.4 (última fila de la tabla de routing).

---

## 2. Clasificación de datos

SICA opera con cinco categorías de datos. Las reglas de cifrado, acceso y retención son distintas para cada una.

| Categoría | Definición | Ejemplos | Reglas distintivas |
|---|---|---|---|
| **PHI** | Información de salud asociable a un individuo identificable | Historia clínica con DNI, ecografía con nombre, reportes con HC | Procesamiento local default. Audit log obligatorio. Cifrado en reposo y tránsito. RBAC estricto. |
| **PHI desidentificada** | Información clínica sin identificadores directos ni indirectos que permitan reidentificación razonable | Historia clínica con DNI removido, fechas desplazadas, ubicación generalizada a región | Puede usarse para evals, benchmarks, fine-tuning. Sigue requiriendo cifrado. Revisión de reidentificación cada 6 meses. |
| **Datos sintéticos** | Pacientes generados artificialmente por médicos o LLMs bajo supervisión, sin correspondencia con personas reales | Pacientes para synthetic patient testing (STRATEGY § 10.4), casos adversariales | Sin restricciones de PHI. Deben estar **claramente marcados** en metadata. Pueden enviarse a cualquier modelo. |
| **Datos operacionales** | Métricas, logs, telemetría, eventos de uso del sistema | Tiempos de respuesta, tasas de error, eventos aceptado/editado/rechazado | Sin PHI por construcción. Pueden agregarse para análisis. Retención según política operativa. |
| **Datos de configuración** | Prompts, schemas FHIR, políticas de routing, fixtures de evaluación | `prompt_registry/`, `evals/fixtures/` | Versionados en git. No contienen PHI bajo ninguna circunstancia. |

**Regla de oro de clasificación:** ante cualquier duda, el dato se clasifica al nivel más restrictivo. Mover un dato hacia abajo en la jerarquía (de PHI a desidentificada, por ejemplo) requiere proceso explícito (sección 6 de este documento).

---

## 3. Cifrado

### 3.1 En reposo

| Dato | Estándar |
|---|---|
| Object storage (PDFs, imágenes, documentos clínicos) | AES-256 con CMEK (Customer-Managed Encryption Keys) |
| Base de datos transaccional (Postgres / Supabase) | AES-256, llaves gestionadas por proveedor + opción CMEK para PHI |
| Backups | AES-256, llaves separadas del primary |
| Logs con potencial PHI | AES-256 + acceso restringido |

### 3.2 En tránsito

| Trayecto | Estándar |
|---|---|
| Cliente → API SICA | TLS 1.3+ con ciphers modernos (sin TLS 1.0/1.1) |
| API SICA → modelos cloud (Gemini, Claude) | TLS 1.3+, sólo proveedores con compliance documentado |
| Conector → HIS / SIHCE del partner | TLS 1.3+ o VPN site-to-site según preferencia del partner |
| Replicación entre regiones (cuando aplique) | TLS 1.3+ + cifrado a nivel de aplicación |

`[TODO]` — Validar con asesor de seguridad si TLS 1.2 con ciphers AEAD modernos sigue siendo aceptable para integraciones con HIS legacy que no soporten 1.3.

### 3.3 Gestión de llaves

- **KMS recomendado:** Google Cloud KMS o equivalente del proveedor de infraestructura elegido.
- **Llaves nunca en código.** Nunca en repositorios, nunca en contenedores de imagen. Sólo en KMS o secret manager con audit log.
- **Rotación:** cada 90 días para llaves de datos en reposo; cada 30 días para llaves de API a proveedores externos.
- **Separación de roles:** la persona que opera el sistema no es la misma que tiene acceso a las llaves maestras. `[TODO — definir owner formal de KMS cuando exista el rol]`.
- **Llaves perdidas o comprometidas:** rotación inmediata + revocación + re-cifrado de datos afectados. Documentar en post-mortem (ver `incident-response.md`).

---

## 4. Acceso

### 4.1 Control de acceso

- **RBAC obligatorio.** Acceso a recursos clínicos se concede por rol, no por identidad individual.
- **Principio de mínimo privilegio.** Cada rol tiene acceso al mínimo de datos y operaciones necesarios para su función.
- **Just-in-time access para producción.** Acceso a entornos con PHI real es solicitado, aprobado y temporal — no permanente.

### 4.2 Roles iniciales (Fase 1)

`[TODO — formalizar con asesor legal en cuanto exista el rol de DPO]`

| Rol | Acceso a PHI | Acceso a infra | Aprueba |
|---|---|---|---|
| Founder / CTO | Sí (cuando aplique) | Total | Cambios de política |
| Ingeniero ML | PHI desidentificada + sintética | Entornos de dev/staging | Cambios de modelos |
| Líder clínico | PHI (para validación) | Read-only | Validaciones clínicas |
| Médico revisor del partner | PHI de sus pacientes | Acceso de aplicación, no infra | Aceptación/edición de outputs |
| Auditor externo | Audit logs (sin contenido PHI) | Read-only audit | Reportes de cumplimiento |

### 4.3 Autenticación

- **MFA obligatorio** para cualquier acceso a entornos con PHI real (producción y staging que use copias de PHI).
- **SSO** cuando exista (multi-cliente). `[TODO — implementación pospuesta a R5]`.
- **API keys** para servicios automatizados, rotación cada 30 días, scope limitado.

### 4.4 Audit log de accesos

Cada acceso a PHI queda registrado con:

- Identidad del actor (humano o servicio).
- Timestamp.
- Operación (read / write / list / delete).
- Recurso afectado (paciente, encounter, documento — identificadores opacos).
- Resultado (success / denied).
- Origen (IP, agente, contexto de aplicación).

Audit logs son **immutables**, almacenados separados del sistema operacional, y retenidos por mínimo 5 años o lo que exija la regulación, lo que sea mayor. `[TODO — confirmar plazo exacto con asesor legal de Ley 29733]`.

---

## 5. Retención y eliminación

### 5.1 Política de retención

| Tipo de dato | Retención por default | Configurable por cliente |
|---|---|---|
| PHI en producción | Política del cliente, mínimo legal peruano | Sí — el contrato con el partner define el plazo concreto |
| PHI desidentificada para evals | 24 meses, revisión anual | Sí |
| Logs con potencial PHI | 12 meses máximo | No — límite duro |
| Audit logs | ≥5 años | No — límite duro mínimo |
| Datos sintéticos | Indefinido | Sí |
| Datos operacionales (métricas, telemetría) | 24 meses | Sí |

`[TODO]` — Confirmar plazo mínimo legal peruano para retención de historia clínica electrónica (Ley 30024 / RENHICE y reglamento).

### 5.2 Derecho a eliminación

Coherente con Ley 29733, SICA debe atender solicitudes de:

- **Acceso** del titular a sus datos.
- **Rectificación** de datos inexactos.
- **Supresión** (derecho al olvido) cuando proceda.
- **Oposición** al tratamiento cuando proceda.
- **Portabilidad** del dato en formato estructurado.

Plazo de respuesta: el que defina la Ley 29733 y su reglamento. `[TODO — fijar plazo exacto con asesor legal]`.

### 5.3 Eliminación técnica

- **Soft delete** en aplicación: marca como eliminado, queda fuera de queries operativas.
- **Hard delete** en backend: ejecutado en ventana periódica (≤30 días desde solicitud), elimina del primary + backups + índices vectoriales.
- **Audit log de eliminación:** la eliminación queda registrada (qué, cuándo, por orden de quién), aunque el contenido se borre. La huella de auditoría no se borra.

---

## 6. Desidentificación

### 6.1 Cuándo se requiere

Todo dato que salga del entorno operativo del partner para:

- Evaluaciones técnicas (benchmarks, eval suite).
- Fine-tuning de modelos.
- Compartir con terceros (investigadores, asesores externos).
- Almacenar en entornos que no son el primary de producción.

debe pasar por desidentificación auditable **antes** de salir.

### 6.2 Identificadores a eliminar / transformar

Basado en el estándar HIPAA Safe Harbor adaptado a contexto peruano. **Lista mínima**; cada cliente puede agregar identificadores adicionales.

| Categoría | Identificadores | Acción |
|---|---|---|
| **Directos** | Nombre completo, DNI/CE/pasaporte, número de historia clínica, dirección exacta, teléfonos, email, números de cuenta | Eliminar |
| **Directos institucionales** | Nombre de la clínica, código de IPRESS, identificadores de profesional médico | Eliminar o pseudonimizar según uso |
| **Indirectos** | Fechas (excepto año), edad si >89 años, código postal completo | Generalizar (año, rango de edad, distrito o departamento) |
| **Imágenes** | Texto incrustado en ecografías con nombre/HC, metadatos EXIF | Remover OCR-detectables + scrub de metadata |
| **Texto libre** | Mención del nombre en notas médicas, referencias familiares específicas | Detección por NER + revisión humana |
| **Identificadores combinados** | Combinaciones que permitan reidentificación (ej: edad rara + condición rara + fecha) | Evaluar k-anonymity ≥5 antes de exportar |

### 6.3 Proceso de desidentificación

1. **Pipeline técnico ejecuta** la desidentificación según la tabla 6.2.
2. **Validación automatizada** corre tests de reidentificación adversariales contra el output.
3. **Validación humana** — un médico revisor confirma que el dataset desidentificado mantiene utilidad clínica y no expone identidad.
4. **Firma del proceso** — el founder o líder clínico firma (digital o equivalente) la salida del dataset desidentificado. Sin firma, no sale.
5. **Audit log** — quién pidió la desidentificación, qué dataset entró, qué salió, hash de la salida, quién firmó, cuándo.

`[TODO]` — Definir herramientas técnicas concretas (Presidio, scrubadub, custom). Decisión pospuesta a R0.

### 6.4 Validación periódica

Cada 6 meses, una muestra de datasets desidentificados pasa por un proceso de **reidentificación adversarial**: ¿podría un atacante con acceso a datos públicos peruanos reidentificar a un paciente? Si la respuesta es sí, el dataset se retira de uso hasta nueva desidentificación.

---

## 7. Modelos AI y PHI

Política de routing canónica. Esta tabla extiende STRATEGY § 11.4 con el lente de PHI explícito. **Cualquier cambio en esta tabla requiere ADR.**

| Modelo | Lugar de ejecución | PHI real | PHI desidentificada | Datos sintéticos | Notas |
|---|---|:---:|:---:|:---:|---|
| **MedGemma 4B / 27B** (local) | On-prem o GPU dedicada del entorno controlado | ✅ Permitido (default) | ✅ | ✅ | Default para PHI. Coherente con STRATEGY § 11.4 |
| **MedSigLIP** (local) | On-prem | ✅ Permitido para embeddings | ✅ | ✅ | Encoder, no genera texto. Bajo riesgo de fuga vía output |
| **Document AI** (Google Cloud) | Google Cloud, región controlada | ⚠️ Sólo con DPA firmado + región configurada + política explícita | ✅ | ✅ | OCR; revisar términos de procesamiento por proveedor antes de R0 |
| **Gemini 2.5 Flash / Pro** (Google Cloud) | Google Cloud | ⚠️ Sólo con DPA firmado + política explícita por workflow + audit log + consentimiento documentado | ✅ | ✅ | Escalamiento puntual. Cada uso es decisión deliberada por workflow |
| **Anthropic Claude** (API) | Anthropic | ❌ **NUNCA en Fase 1** | ⚠️ Sólo para desarrollo y eval | ✅ | Permitido sólo sobre datos sintéticos o desidentificados para desarrollo. Revisar en R5+ con DPA explícito si la necesidad clínica aparece |
| **OpenAI GPT / otros** | Externo | ❌ No permitido en Fase 1 | ❌ | ⚠️ Caso por caso | No es modelo elegido por SICA. Si aparece necesidad puntual, requiere ADR |

### 7.1 Reglas operativas

- **PHI real a cloud sólo con tres condiciones simultáneas:** DPA firmado, política de workflow explícita, audit log activo. La ausencia de cualquiera de las tres bloquea el escalamiento.
- **El médico recibe indicación visible** cuando un output fue generado con escalamiento cloud sobre su PHI (transparencia frente al usuario final clínico).
- **Si un workflow rutinariamente requiere escalamiento cloud,** se evalúa si justifica infraestructura local mayor (mover de L4 puntual a A100 dedicado).
- **Anthropic Claude está específicamente vetado para PHI real en Fase 1.** Razón: Claude es el modelo que asiste el desarrollo de SICA (este mismo asistente). Usar el mismo proveedor en runtime clínico crea dependencia y conflicto operacional con la separación entre entorno de desarrollo y de producción. La política se revisa en R5+ si aparece necesidad clínica concreta.

### 7.2 Cambios a la política de routing

Cualquier modificación de esta tabla (agregar modelo, mover ✅/⚠️/❌, cambiar región, cambiar default) requiere:

1. **ADR explícito** con `Status: Proposed`.
2. **Revisión del líder clínico** (impacto en seguridad clínica) y del responsable de seguridad (impacto regulatorio).
3. **Aprobación del founder.**
4. **Comunicación al partner** antes del despliegue.

No se cambia esta política con un PR de configuración. Es decisión arquitectónica trazada en ADR.

---

## 8. Excepciones documentadas

Las excepciones a las reglas anteriores no se prohíben — se documentan. Una excepción no registrada es una violación de política.

### 8.1 Cómo registrar una excepción

Cada excepción se registra en un documento estructurado que incluye:

| Campo | Contenido |
|---|---|
| ID | EXC-YYYY-NNNN |
| Política excedida | Referencia a sección de este documento |
| Razón | Justificación clínica / técnica / operacional |
| Alcance | Qué workflow / qué datos / qué duración |
| Mitigaciones | Controles compensatorios aplicados |
| Aprobado por | Founder + líder clínico + (si aplica) DPO |
| Fecha de inicio | YYYY-MM-DD |
| Fecha de revisión | YYYY-MM-DD (máximo 6 meses) |
| Plan de cierre | Cómo y cuándo se retira la excepción |

`[TODO]` — Crear `docs/security/exceptions/` con plantilla y registro de excepciones cuando aparezca la primera.

### 8.2 Excepciones permanentes prohibidas

Ninguna excepción puede:

- Eliminar el audit log de operaciones con PHI.
- Permitir PHI real a Claude en Fase 1.
- Bypass MFA en producción.
- Almacenar PHI sin cifrado en reposo.
- Transmitir PHI sin cifrado en tránsito.

Estas reglas son límites duros, no flexibles por excepción.

---

## Referencias

- `STRATEGY.md` § 11 (arquitectura técnica), § 13 (marco regulatorio peruano), § 18 (riesgos).
- `docs/security/ley-29733-compliance.md` — mapeo regulatorio explícito.
- `docs/security/threat-model.md` — vectores de ataque considerados.
- `docs/decisions/0003-security-and-phi-policy.md` — ADR que adopta esta política.
- Ley 29733 (Protección de Datos Personales del Perú) y su reglamento.
- Ley 30024 (RENHICE) y su reglamento.
- IMDRF — principios para software médico.
- OMS — Ethics and governance of artificial intelligence for health.
