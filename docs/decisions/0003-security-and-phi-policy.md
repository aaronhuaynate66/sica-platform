# 0003. Security and PHI handling policy

- **Status:** Accepted
- **Date:** 2026-05-21
- **Deciders:** Aaron Huaynate (founder / CTO)
- **Tags:** security, phi, compliance, regulatory, ley-29733
- **Related:** [ADR 0001](0001-monorepo-turborepo.md) (monorepo), [ADR 0002](0002-living-roadmap-system.md) (living roadmap)

## Context

R0 (Mes 0-2) va a tocar **historias clínicas obstétricas reales desidentificadas** del partner fundador (150-200 casos) para construir el benchmark inicial. Coherente con STRATEGY § 7 (gate de salida R0: MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas) y `docs/roadmap.md` § R0.

Antes de que el primer PDF real entre al entorno de SICA, hace falta formalizar **políticas operativas y regulatorias** que cubran:

1. Manejo de PHI (cifrado, acceso, retención, desidentificación).
2. Cumplimiento de Ley 29733 (Protección de Datos Personales del Perú): inscripción ANPD, DPO, DPIA, consentimiento informado, encargados de tratamiento, transferencias internacionales.
3. Plan de respuesta a incidentes con plazos legales documentados.
4. Modelo de amenazas que reconozca vectores específicos de healthtech AI (prompt injection, exfiltración LLM, reidentificación).
5. Política explícita de routing de modelos AI con relación a PHI, particularmente:
   - PHI real procesada por default en MedGemma local.
   - Gemini cloud sólo bajo condiciones documentadas.
   - **Anthropic Claude vetado para PHI real en Fase 1** porque Claude es a la vez el modelo que asiste el desarrollo de SICA y un proveedor cloud externo — usar la misma vía en runtime clínico crea conflicto operacional y dependencia mal posicionada.

STRATEGY § 13 (marco regulatorio peruano), § 11.1 (principio: PHI sensible nunca sale a cloud sin política explícita), § 11.4 (política de routing de modelos), § 18 (riesgos), y el issue [#15](https://github.com/aaronhuaynate66/sica-platform/issues/15) (P0 bloqueante R0) convergen en pedir esta formalización ahora.

Sin esta formalización, cualquier corrida con datos reales es exposición legal y reputacional. SICA es pre-producto: el costo de formalizar ahora es bajo (documental) y el costo de no formalizar después es alto (incidentes regulatorios, pérdida de confianza del partner, retraso de R0).

## Decision

**SICA adopta como política normativa el conjunto de documentos publicados en `docs/security/`**, junto con la política de divulgación responsable en `SECURITY.md` (raíz). Concretamente:

1. **`SECURITY.md`** (raíz) define cómo reportar vulnerabilidades, qué se considera vulnerabilidad, tiempos de respuesta, y un disclaimer de estado pre-producto. GitHub lo expone automáticamente en la pestaña Security del repo.

2. **`docs/security/data-handling.md`** establece la política operativa de PHI:
   - Cinco principios fundamentales (procesamiento local default para PHI, audit log obligatorio, abstención sobre alucinación, escalamiento cloud deliberado por workflow, PHI nunca sale sin política).
   - Clasificación en 5 categorías de datos con reglas distintas.
   - Cifrado en reposo (AES-256 + CMEK) y tránsito (TLS 1.3+).
   - RBAC + MFA obligatorio + audit log de cada acceso a PHI.
   - Política de retención y eliminación coherente con derechos del titular.
   - Proceso de desidentificación auditable con firma obligatoria.
   - Tabla canónica de routing de modelos vs PHI (con Claude vetado en Fase 1).
   - Mecanismo formal de excepciones documentadas.

3. **`docs/security/ley-29733-compliance.md`** mapea cada obligación de Ley 29733 al estado actual de SICA, identifica brechas, owners y deadlines. Define la lista numerada de **bloqueantes para tocar PHI real**.

4. **`docs/security/incident-response.md`** define tipos de incidente, severidades, roles (con TBDs realistas para Fase 1), matriz de escalamiento, playbook de brecha PHI paso a paso, plazos legales, comunicación interna/externa, y template de post-mortem blameless.

5. **`docs/security/threat-model.md`** documenta el modelo STRIDE aplicado a SICA + vectores específicos de healthtech AI (prompt injection PDF/UI, exfiltración LLM, reidentificación, compromiso de API keys, training data poisoning, hallucination).

Cualquier cambio sustantivo en estas políticas requiere un nuevo ADR que supersede o complemente este.

## Consequences

### Positive

- **Trazabilidad regulatoria.** SICA puede demostrar — ante asesor regulatorio externo, ante el partner durante negociación de DPA, ante auditor ANPD — que las políticas existen, son consistentes entre sí y están firmadas.
- **Claridad operativa.** Decisiones cotidianas (qué dato puede ir a qué modelo, cómo se desidentifica un dataset para evals, qué se hace si se sospecha brecha) tienen respuesta documentada en lugar de improvisarse.
- **Bloqueantes explícitos para PHI real.** Lista numerada (`ley-29733-compliance.md` § "Bloqueantes para tocar PHI real") que cualquier miembro del equipo o asesor puede verificar antes de autorizar el primer dato real.
- **Política consistente sobre Claude.** Veto en Fase 1 documentado con justificación. Si en R5+ aparece necesidad clínica, la decisión de levantarlo requiere un ADR nuevo, no un cambio de configuración silencioso.
- **Base para DPA con partner.** El DPA negocia sobre políticas concretas, no sobre principios vagos.
- **Cierre del issue #15** (P0 bloqueante R0).

### Negative

- **Overhead documental.** Estos documentos requieren mantenimiento. Cada cambio en stack, modelo o regulación implica revisión y actualización. Mitigación: las políticas se revisan al cierre de cada release como parte del proceso, no como tarea adicional.
- **Riesgo de documentación que se desincroniza de la realidad.** Si las políticas dicen una cosa y el código hace otra, la situación regulatoria empeora. Mitigación: gates de CI que validen aspectos comprobables (no secretos en código, no PHI en logs, configuración de cifrado).
- **Asumimos plazos legales conservadores** (72h notificación ANPD como referencia GDPR) hasta validación con asesor externo. Algunos plazos reales pueden ser más cortos. Mitigación: TODOs explícitos marcados para validación con asesor; precaución por defecto al lado más estricto.
- **Veto a Claude en runtime clínico** descarta una vía técnica que podría ser útil. Mitigación: política revisable vía ADR cuando exista necesidad clínica concreta y un DPA específico con Anthropic en condiciones aceptables.
- **Documentos largos.** El conjunto suma >1000 líneas. Onboarding requiere lectura. Mitigación: SECURITY.md sirve como entry point; el resto es referencia consultable.

## Alternatives considered

### Alternativa A: No documentar formalmente (postergar a Fase 2)

**Forma:** seguir con la política implícita en STRATEGY § 13 + decisiones ad-hoc cuando aparezcan casos concretos.

**Por qué no:**
- Issue #15 lo marca como P0 bloqueante R0. Sin formalización, no se toca PHI real.
- La regulación peruana (Ley 29733) requiere documentación específica (DPIA, registros de actividades, medidas técnicas) antes del primer tratamiento. Postergar significa retrasar R0.
- DPA con partner fundador requiere política concreta del lado de SICA. Sin política, no hay DPA. Sin DPA, no hay datos. Sin datos, no hay R0.
- El costo de formalizar ahora (días de trabajo del founder + revisión legal) es mucho menor que el costo de improvisar bajo presión ante un incidente real.

### Alternativa B: Adoptar políticas externas estándar (HIPAA / SOC 2 / ISO 27001) sin adaptación

**Forma:** publicar "SICA cumple HIPAA" o equivalente y usar plantillas estándar US/EU.

**Por qué no:**
- **Jurisdicción incorrecta.** HIPAA es US, GDPR es EU. SICA opera en Perú bajo Ley 29733. Aunque hay convergencia en principios (consentimiento, derechos del titular, notificación de brechas), los plazos exactos, autoridades, requisitos de inscripción y plantillas son distintos.
- Adoptar HIPAA sin ser entidad cubierta no agrega valor regulatorio en Perú y puede ser engañoso ("cumplimos HIPAA pero no aplica aquí").
- SOC 2 e ISO 27001 son válidos como complementos futuros (R5+ cuando aparezcan clientes que los exijan), pero no resuelven la pregunta peruana de hoy.
- Sí se **toma inspiración** de los controles técnicos (HIPAA Safe Harbor para desidentificación, principios NIST AI RMF para modelo de amenazas), pero la política base es peruana.

### Alternativa C: Política mínima viable + iterar

**Forma:** un único documento corto (`SECURITY.md` + 1 página de política PHI) que cubra lo básico y se expanda con la operación.

**Por qué no:**
- El issue #15 lista 8 secciones explícitas que deben estar cubiertas. Un documento corto las cubre superficialmente, no operacionalmente.
- Cuatro documentos especializados (data-handling, ley-29733, incident-response, threat-model) reflejan que son cuatro audiencias distintas y cuatro flujos distintos. Mezclarlos produce un documento que nadie lee completo y que pierde precisión.
- Cada documento es lo suficientemente largo para ser útil, lo suficientemente corto para ser navegable (entre 200 y 300 líneas cada uno).

### Alternativa D: Contratar asesor regulatorio antes de escribir nada

**Forma:** esperar a tener asesor legal contratado y dejar que él/ella escriba las políticas.

**Por qué no:**
- Asesor legal cuesta tiempo y dinero. Es mejor llegar con borrador estructurado para que revise y corrija, no con página en blanco para que escriba.
- El asesor sabe regulación; SICA sabe su arquitectura. Las políticas que sirven combinan ambas vistas. Empezar por el lado regulatorio puro produce documentos genéricos que no operacionalizan la realidad técnica.
- Esto **no excluye** que el asesor revise; al contrario, está marcado como TODO explícito en cada documento y como bloqueante en `ley-29733-compliance.md`.

## References

- [Ley 29733 — Ley de Protección de Datos Personales del Perú](https://www.gob.pe/institucion/minjus/normas-legales/243470-29733) y su reglamento.
- [Ley 30024 — Registro Nacional de Historias Clínicas Electrónicas (RENHICE)](https://www.gob.pe/institucion/minsa/normas-legales/192893-30024).
- [IMDRF — Software as a Medical Device documents](https://www.imdrf.org/).
- [OMS — Ethics and governance of artificial intelligence for health](https://www.who.int/publications/i/item/9789240029200).
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/).
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework).
- [NIST SP 800-61 — Computer Security Incident Handling Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf).
- `STRATEGY.md` § 11.1, § 11.4, § 13, § 18.
- `docs/roadmap.md` § R0 (anonimización auditable).
- GitHub issue [#15](https://github.com/aaronhuaynate66/sica-platform/issues/15) (P0 bloqueante R0).

## Migration log

Vacío. Esta es la primera versión de la política. Cambios futuros se anotan aquí (fecha, naturaleza del cambio, ADR superseder si aplica).

| Fecha | Cambio | Autor | ADR superseder |
|---|---|---|---|
| 2026-05-21 | Creación inicial | Aaron Huaynate | — |
