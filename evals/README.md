# evals/

Suite de evaluación clínica de SICA. Implementa los **siete pilares** descritos en `STRATEGY.md` § 10:

1. Factual accuracy (span-level)
2. Critical omissions
3. Hallucination benchmark
4. Physician disagreement scoring
5. Longitudinal consistency
6. Temporal reasoning
7. Synthetic patient testing

## Estado

Esqueleto. La suite real arranca en R0 con el primer dataset retrospectivo del partner fundador (ver `docs/roadmap.md` § R0).

## Estructura planeada

```
evals/
├── README.md                    ← este archivo
├── fixtures/                    ← casos sintéticos commiteables (NUNCA PHI real)
├── datasets/                    ← datasets reales (gitignored, en object storage)
├── ground_truth/                ← labels de médicos en doble ciego (gitignored)
├── harness/                     ← código del runner: input → modelo → métricas
├── metrics/                     ← implementación de cada métrica
└── reports/                     ← outputs de corridas (gitignored)
```

## Principios

- **Test set congelado.** Cambios al test set requieren ADR explícito.
- **Regression antes de merge.** Cualquier cambio de prompt o modelo corre la suite completa.
- **Sin PHI en el repo.** Solo `fixtures/` (sintético, marcado) entra al git.
