# Operating Model — SICA

**Versión 0.1 — PLACEHOLDER**
**Status: esqueleto para Fase 2. Detalle se construye junto con la estructura GitHub y el monorepo.**

---

Este documento describirá cómo SICA opera como **AI-native company** desde día uno. Vive aquí (no en STRATEGY.md) porque es operación interna, no narrativa estratégica.

Cuando arranquemos Fase 2 (construcción de GitHub Org + monorepo + CI/CD), este documento se desarrolla en paralelo. Por ahora, esqueleto.

---

## 1. AI-native company — definición operativa

SICA no es "una startup que usa IA en su producto". Es "una startup que opera con IA en todas sus funciones internas". La diferencia importa:

- **No solo Claude/Cursor para escribir código.**
- **No solo ChatGPT para redactar emails.**
- **Sistema deliberado de orquestación de IA en producto, ingeniería, clínica, GTM, operaciones.**

## 2. Las cinco funciones bajo operación AI-native

### 2.1 Product

- Specs asistidas por IA: cada feature tiene PRD generado/iterado con LLM, con humanos en review.
- Sprint planning con IA: priorización sugerida con basis en feedback médico, métricas de eval, dependencies.
- Issue generation: IA genera tickets desde feedback clínico estructurado.

### 2.2 Engineering

- **Claude Code workflows** para desarrollo asistido.
- **AI PR reviews** automáticos (revisor humano final, IA primera capa).
- **AI architecture analysis** antes de decisiones técnicas mayores.
- **AI documentation generation** mantenida actualizada por bots.
- **AI sprint generation** desde el roadmap living.

### 2.3 Clinical

- **AI annotation workflows** para que médicos validen ground truth más rápido.
- **AI-assisted validation** de eval suites — la IA sugiere casos edge antes de que el médico los detecte.
- **AI synthesis** de feedback médico → categorización automática → priorización.

### 2.4 GTM

- **AI research** de prospects (clínicas, KOLs).
- **AI CRM enrichment** automático.
- **AI sales prep** para cada conversación.
- **AI follow-up drafting** con humano en aprobación.

### 2.5 Operations

- **AI roadmap engine:** IA actualiza el roadmap living, detecta bloqueos, sugiere prioridades, reorganiza sprints (humanos confirman).
- **AI bug triage.**
- **AI weekly digest** del estado de la empresa para founders.

---

## 3. Engineering rituals (a definir en Fase 2)

- Daily: async standup con AI-summarized highlights.
- Weekly: sprint review + retrospective + AI-generated trend analysis.
- Monthly: architecture review + AI-flagged technical debt.
- Quarterly: roadmap recalibration with AI scenario modeling.

## 4. Stack de tooling AI-native (a detallar en Fase 2)

- Code: Claude Code, Cursor, GitHub Copilot.
- Reviews: Anthropic API for custom PR reviewers.
- Project management: Linear + AI assist via API.
- Docs: AI-generated and AI-maintained.
- Comms: AI summarization of Slack/email.

## 5. Anti-patrones evitados

- "AI for the sake of AI" — no usamos IA donde no agrega valor real.
- AI sin humano en review en decisiones críticas (clínicas, hiring, financieras).
- Black box AI — todo output relevante traza a quién/qué lo generó.

---

**Para desarrollar en Fase 2:** templates concretos, integraciones específicas, métricas de impacto, governance del uso de IA interna.
