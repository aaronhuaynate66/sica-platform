# Fundraising Narrative — SICA

**Versión 0.1 — BORRADOR**
**Status: PARA USO EN FUNDRAISING ÚNICAMENTE — no compartir con asesores clínicos ni con prospects de partners clínicos.**

---

## Cómo leer este documento

Este es el documento de narrativa VC de SICA. Es **distinto en tono y énfasis** del `STRATEGY.md` por una razón deliberada:

- `STRATEGY.md` está escrito para validación crítica — minimiza overclaim para que asesores clínicos y regulatorios confíen.
- `fundraising-narrative.md` está escrito para **transmitir ambición y categoría** — usa el lenguaje que un partner de a16z o Founders Fund decodifica.

Ambos son verdaderos. Uno habla a quien filtra; el otro habla a quien apuesta.

**Cuándo usar este documento:**

- Pitch deck draft.
- Preparación de conversación con seed VC.
- Memo escrito para due diligence.

**Cuándo NO usar este documento:**

- Conversaciones con asesor regulatorio peruano.
- Conversaciones con directores médicos de prospects.
- Material público (web, prensa, redes).

---

## 1. The one-liner

> **SICA is the first Clinical Intelligence Infrastructure for maternal and early-life care in emerging markets — a longitudinal cognitive layer that connects pregnancy, birth, neonatal care, and pediatric continuity, mounted on top of existing hospital systems, with multimodal AI, explainability by design, and a regulatory-aware go-to-market.**

Variante corta:

> **The AI operating system for maternal and early-life care.**

Variante para foundation VCs (Khosla, Founders Fund):

> **We're building Palantir Gotham for maternal-child healthcare in emerging markets.**

---

## 2. Why Now (versión deck)

Eight forces converged in 2025-2026 that made SICA impossible in 2022:

1. **Medical LLMs went open-weight.** Google released MedGemma (4B multimodal, 27B text-only) and MedSigLIP. For the first time, clinical inference can run locally on PHI without sending data to a third-party cloud.
2. **Multimodal AI hit production maturity.** Gemini natively understands medical PDFs, not just OCR.
3. **Inference costs collapsed >10x.** A NVIDIA L4 on GCP costs USD 0.71/hour. MVP infrastructure fits in USD 500/month.
4. **FHIR R4 consolidated globally.** US (CMS rule), EU (EHDS), and now LatAm. Peru's first national interoperability hackathon happened June 2025.
5. **Peru accelerated digital health regulation.** RENHICE law updated, SIHCE accreditation directive approved March 2025.
6. **Physician burnout is structural.** >50% in OB/GYN and pediatrics globally. Maternal-fetal medicine and neonatology specifically.
7. **Healthcare fragmentation is extreme in LatAm.** Unlike US where Epic owns 30%+, Peru has dozens of legacy HIS, partial integrations, paper, PDFs, WhatsApp. That fragmentation is the moat.
8. **Digital-native physicians are entering practice.** Residents trained 2024-2028 expect Linear/Notion-grade tools, not paper-based workflows.

**The window is ~3 years. After 2029, someone owns this. The question is who.**

---

## 3. The market

### 3.1 The opportunity sized correctly

`[TODO crítico: estos números necesitan validación con datos primarios. Lo que sigue es un FRAMEWORK para llenarlos, no los números finales]`

**TAM — Total Addressable Market:**
- Global maternal-child clinical AI infrastructure spend by 2030: `[research needed]`
- Reference: global healthcare AI market projected USD 100B+ by 2030 (multiple analyst sources).

**SAM — Serviceable Addressable Market:**
- Private hospitals and clinics in LatAm with OB-GYN + neonatal + pediatric services.
- Peru: estimated ~200 private clinics meeting ICP criteria. `[validate]`
- LatAm core (Peru + Chile + Colombia + Mexico + Brazil): estimated ~3,000-5,000. `[validate]`

**SOM — Serviceable Obtainable Market (5-year):**
- Year 5 realistic target: 100-150 clinics across 3 countries.
- ARR potential: USD 4-6M at current pricing assumptions.

**Más importante que el número absoluto:** la **expansión vertical** (de materno-infantil a cardiología crónica, oncología seguimiento, salud mental con continuidad) multiplica el TAM 4-6x. Esa es la apuesta de plataforma del año 4+.

### 3.2 Comparables financieros

`[TODO: completar con datos reales de cada ronda]`

| Empresa | Vertical | Última ronda | Valuación | Mercado |
|---|---|---|---|---|
| **Abridge** | Ambient scribe | Series D | USD 2.75B+ (2024) | US enterprise |
| **Nabla** | Ambient scribe | Series B | USD 200M+ (2024) | US, EU |
| **Ambience Healthcare** | Ambient + summarization | Series C | USD 1B+ (2024) | US |
| **Hippocratic AI** | LLM clínico | Series B | USD 2B (2024) | US enterprise |
| **Glass Health** | Clinical reasoning | Seed/Series A | `[verificar]` | US, B2C/B2B |
| **OpenEvidence** | Knowledge retrieval | Series A+ | USD 1B+ (2024) | US clínicos |

**El thesis investor:** estos valuations son por verticales adyacentes en US. SICA construye una categoría diferente (no scribe, no Q&A) en mercados nuevos (LatAm). Si **una** de esas trayectorias se reproduce con SICA, retorno claro.

---

## 4. The product, told big

SICA isn't a tool. It's an **operating system layer** for maternal-child care.

It does five things together that no incumbent does:

1. **Reads everything.** PDFs, HL7v2, FHIR, ultrasounds with embedded text, handwritten notes. Multimodal ingestion from day one.
2. **Connects everything.** Pregnancy → birth → neonate → CRED follow-up. The mother and baby are linked entities in a longitudinal graph.
3. **Reasons over time.** Risk evolution across the pregnancy, gaps in prenatal package, deviations from protocol.
4. **Explains everything.** Every output traces to a source with timestamp and confidence. No black boxes for physicians.
5. **Embeds anywhere.** No new HIS. SICA mounts on top of what hospitals already have.

This combination is what we mean by Clinical Intelligence Infrastructure. **It's the missing fourth layer above storage, processing, and communication systems.**

---

## 5. The moat, told seriously

The moat is not the model. Models commoditize. The moat is the **longitudinal maternal-child dataset** that emerges from the Clinical Data Flywheel (see STRATEGY.md § 9):

- **It's longitudinal.** A competitor entering OB in 2027 can generate volume of summaries. But they can't generate 3 years of mother→baby→CRED continuity. That requires calendar time, not capital.
- **It's local.** MedGemma was trained on US/EU clinical data. Peruvian obstetric practices (MINSA prenatal package, cesarean criteria, local UCIN protocols) differ. The fine-tuning value compounds.
- **It's structured feedback.** RLHF-grade signal from physician edits, categorized by type (factual fix, critical addition, style edit, removal). This is qualitative data competitors don't have.

Layered on top: **regulatory positioning** (assistive vs. autonomous), **clinical credibility** (KOLs, society relationships, residency programs), and **deep workflow integration** (FHIR backbone + embedded UI launch).

Each layer alone is weak. Together they create defensibility that lasts beyond any single model generation.

---

## 6. The wedge, told strategically

`[Para inversores conservadores que dicen "qué construyen primero":]`

We start with one thing: **the obstetric longitudinal summary** in **one founding partner clinic in Lima**. That's it. Months 2-5.

Then we build the Clinical Memory Graph one release at a time:

- R1 Summary → first layer of the graph
- R2 Shadow + checklist → reasoning engine trained on local protocols
- R3 Handoff → graph extends to mother↔baby relationships
- R4 Pre-anesthesia brief → reasoning under time pressure
- R5 CRED + multi-site → longitudinal continuity closed + replicable product

By month 18, we don't have "a tool that summarizes." **We have the first Clinical Intelligence Infrastructure for maternal-child care in LatAm, with one anchor customer renewed, a second site signed, validated clinical outcomes, and a regulatory positioning that scales.**

The wedge is humble. The destination is a category.

---

## 7. The team

`[TODO: completar con perfiles reales de los founders]`

The cliché in healthtech is "we need a clinical co-founder." It's true but insufficient. SICA needs:

- **A founder who can sell to Peruvian directores médicos** while pitching to Sand Hill Road. Bilingual, bi-cultural, comfortable in both rooms.
- **A founder who has built AI systems at production scale**, not just demos. Specifically: someone who has shipped LLM-powered products and knows what eval infrastructure must look like.
- **A clinical leader** with credibility in the specialty — not generic "MD advisor" but specifically OB/GYN or neonatology, ideally with academic affiliation and a publication record.

`[Completar bios cuando estén]`

---

## 8. The ask

`[TODO: ajustar a la realidad financiera del momento de pitch]`

**What we're raising:** seed round of USD `[X]` to fund Phase 1 (18 months) — get to:

- R5 in production at founding partner
- Site 2 onboarded and renewed
- Documented clinical validation (factual accuracy >95%, handoff completeness >95%)
- 3 KOL advisors signed
- First clinical paper or poster published
- Path to Series A on Phase 2 (LatAm expansion + platform evolution)

**Use of funds breakdown** (see STRATEGY.md § 15.4 for detail).

**What we want from investors:** capital, yes, but specifically:

- Healthcare AI domain expertise on the board.
- Introductions to regulatory specialists in LatAm.
- Pattern recognition on go-to-market in enterprise healthcare from US comps.

---

## 9. Why we will win

Three asymmetric advantages that compound:

1. **Founders' positioning.** Few healthtech AI founders have both US AI engineering depth AND deep LatAm clinical access. The intersection is small.

2. **Window of regulatory ambiguity that closes.** Peru's regulatory framework is in formation. Right now, an assistive clinical AI can be built legally. In 2-3 years, a more restrictive interpretation may emerge. We define practice while the window is open.

3. **Data moat that calendar time creates.** Longitudinal maternal-child data requires 3+ years of follow-up. No competitor with more capital can shortcut that.

The combination of **right product** + **right window** + **right team** + **right moat** is what makes SICA a venture-scale bet, not a lifestyle business.

---

## 10. Risks investors will ask about (and our answers)

| Investor concern | Honest answer |
|---|---|
| "LatAm healthcare is hard to sell into" | Yes. That's the moat. The same difficulty that scares horizontal players is what creates the vertical opportunity. |
| "Why not US first?" | US is saturated with Abridge, Nabla, Ambience. LatAm has zero direct competitor with this thesis. We can build a thesis-proving business in Peru, then expand to US/EU with a validated category. |
| "What if regulation tightens?" | Phase 1 product is positioned assistively to stay below dispositivo médico classification. Even if regulation tightens, the architecture (FHIR backbone, multi-model routing, explainability layer) is what regulators want to see. |
| "What if MedGemma 4B underperforms?" | R0 gate explicitly tests this with 150-200 local OB charts before building UI. If fails, we have documented plan B (27B text-only or Gemini default with strict policies). |
| "Healthcare sales cycles will kill you" | True if we sell to large enterprise. We sell to mid-size private clinics with 3-6 month cycles, founder-led, paid pilots. ICP excludes long-sales-cycle accounts. |
| "What's the exit path?" | Strategic acquisition by global healthtech (Epic, Athenahealth, Philips), by emerging-markets healthcare consolidator, or independent path to growth equity. Multiple exits possible at Series B+. |

---

**Fin del documento de fundraising v0.1.**

Próximo paso: completar TODOs marcados antes de exposición a inversores reales. **Este documento NO está listo para pitch hoy** — está listo para iterar con founders y advisors.
