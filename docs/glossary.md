# Glosario — SICA

Definiciones de términos clínicos, técnicos y regulatorios usados en `STRATEGY.md` y documentos relacionados. Útil para onboarding de nuevos miembros del equipo (especialmente ingenieros sin contexto clínico previo, y clínicos sin contexto técnico).

---

## Clínico — obstetricia

- **EG** — Edad gestacional. Semanas + días desde la FUM.
- **FUM** — Fecha de última menstruación. Anchor temporal del embarazo.
- **FPP** — Fecha probable de parto.
- **CPN / Control prenatal** — Visita médica programada durante el embarazo. Paquete mínimo MINSA: 6 controles.
- **RPM** — Ruptura prematura de membranas.
- **GBS** — Streptococcus del grupo B. Tamizaje recolocónico-vaginal entre 35-37 semanas.
- **DG / Diabetes gestacional** — Hiperglucemia detectada por primera vez en el embarazo.
- **Preeclampsia** — Hipertensión + proteinuria + daño orgánico, después de las 20 semanas.
- **Cesárea** — Parto por vía abdominal.
- **Líquido meconial** — Líquido amniótico teñido con meconio (heces fetales) — marcador de estrés fetal.

## Clínico — neonatología y pediatría

- **Apgar** — Score de evaluación neonatal al minuto 1 y 5 (color, frecuencia cardíaca, reflejos, tono, respiración).
- **UCIN** — Unidad de Cuidados Intensivos Neonatales.
- **CRED** — Control de Crecimiento y Desarrollo. Paquete pediátrico MINSA para niños 0-5 años.
- **Tamizaje neonatal** — Pruebas obligatorias post-parto (TSH, fenilalanina, hemoglobina, otoemisiones, otros).
- **Alojamiento conjunto** — Madre y neonato sano en misma habitación postparto.

## Clínico — anestesiología

- **ASA** — American Society of Anesthesiologists. Clasificación de riesgo preanestésico (I sano, II enfermedad sistémica leve, III severa, IV amenaza vida, V moribundo, VI donante).
- **Vía aérea difícil** — Predicción de dificultad para intubación.
- **Brief preanestésico** — Resumen estructurado pre-procedimiento con datos críticos para anestesiólogo.

## Técnico — IA y modelos

- **MedGemma** — Familia de modelos open-weight de Google especializados en comprensión clínica multimodal. Versiones 4B (multimodal) y 27B (text-only).
- **MedSigLIP** — Encoder médico para embeddings, retrieval y clasificación de imágenes. No genera texto.
- **Gemini** — Familia de modelos cloud de Google (Flash, Pro, Flash-Lite). Visión nativa de PDFs.
- **RAG** — Retrieval-Augmented Generation. Búsqueda contextual antes de generación.
- **Embeddings** — Representación vectorial densa de texto/imagen para similitud semántica.
- **pgvector** — Extensión Postgres para vectores. Soporta búsqueda exacta y aproximada (HNSW, IVFFlat).
- **FAISS** — Biblioteca de Facebook para búsqueda vectorial a gran escala.
- **DSPy** — Framework para programación declarativa de LLMs con optimización automática de prompts.
- **LangGraph** — Framework para orquestación de agentes y workflows con estado.
- **Langfuse** — Observabilidad y tracing para aplicaciones LLM.
- **OCR** — Optical Character Recognition. Extracción de texto desde imagen/PDF escaneado.
- **Document AI** — Servicio Google para extracción estructurada de documentos.

## Técnico — datos clínicos

- **FHIR R4** — Fast Healthcare Interoperability Resources, versión 4. Estándar HL7 para representación de datos clínicos. JSON/XML.
- **HL7v2** — Estándar HL7 versión 2. Mensajería pipe-delimited legacy ampliamente usada.
- **HCE / EHR** — Historia Clínica Electrónica / Electronic Health Record.
- **HIS** — Hospital Information System. Sistema operacional hospitalario completo.
- **LIS** — Laboratory Information System.
- **PACS** — Picture Archiving and Communication System. Imágenes médicas (radiología, ecografía).
- **CDS Hooks** — Estándar HL7 para insertar sugerencias contextuales en EHRs.
- **PHI** — Protected Health Information. Información de salud identificable.
- **Desidentificación** — Eliminación o transformación de identificadores directos e indirectos.

## Técnico — arquitectura

- **RBAC** — Role-Based Access Control.
- **SSO** — Single Sign-On.
- **CMEK / EKM** — Customer-Managed Encryption Keys / External Key Manager.
- **Zero-trust** — Modelo de seguridad sin confianza implícita por red.
- **Multi-tenancy** — Aislamiento de datos por inquilino (cliente).
- **Audit trail** — Registro inmutable de operaciones para trazabilidad.

## Regulatorio — Perú

- **MINSA** — Ministerio de Salud del Perú.
- **DIGEMID** — Dirección General de Medicamentos, Insumos y Drogas. Regula dispositivos médicos.
- **SUSALUD** — Superintendencia Nacional de Salud.
- **ANPD / APDP** — Autoridad Nacional de Protección de Datos Personales (MINJUS).
- **Ley 29733** — Ley de Protección de Datos Personales del Perú.
- **Ley 30024** — Ley del Registro Nacional de Historias Clínicas Electrónicas (RENHICE).
- **RENHICE** — Registro Nacional de Historias Clínicas Electrónicas.
- **SIHCE** — Sistema de Información de Historias Clínicas Electrónicas. Sistemas acreditados que interoperan con RENHICE.
- **HISMINSA** — Sistema de información clínica del MINSA para establecimientos públicos.
- **CNV** — Certificado de Nacido Vivo.
- **DPO** — Data Protection Officer / Oficial de Datos Personales.
- **DPIA** — Data Protection Impact Assessment / Evaluación de Impacto en Protección de Datos.
- **Conectatón** — Evento de pruebas de interoperabilidad entre sistemas. Primera nacional en Perú: junio 2025.
- **IPRESS** — Institución Prestadora de Servicios de Salud (públicas o privadas).
- **ENDES** — Encuesta Demográfica y de Salud Familiar. Anual, INEI.

## Regulatorio — internacional

- **IMDRF** — International Medical Device Regulators Forum.
- **HIPAA** — Health Insurance Portability and Accountability Act (US). Estándar de referencia para seguridad de PHI; SICA se inspira en sus controles pero no aplica jurisdiccionalmente.
- **GDPR** — General Data Protection Regulation (EU).
- **OMS** — Organización Mundial de la Salud.

## Comercial — SaaS

- **CAC** — Customer Acquisition Cost.
- **LTV** — Lifetime Value.
- **MRR / ARR** — Monthly / Annual Recurring Revenue.
- **Churn** — Tasa de pérdida de clientes.
- **NRR** — Net Revenue Retention.
- **ICP** — Ideal Customer Profile.
- **AE** — Account Executive (rol de ventas).
- **POC** — Proof of Concept.
- **Shadow mode** — El sistema funciona en producción pero no se muestra al usuario, solo se mide.
- **Modo asistivo** — El usuario ve el output y decide aceptar / editar / rechazar.
- **WAU / MAU** — Weekly / Monthly Active Users.

---

**Nota:** este glosario es vivo. Agregar términos a medida que aparezcan en documentos del repo.
