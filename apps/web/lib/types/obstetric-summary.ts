/**
 * Tipos TypeScript que reflejan los schemas Pydantic del clinical-extractor.
 * Fuente canónica: services/clinical-extractor/src/clinical_extractor/schemas.py
 *
 * IMPORTANTE: si cambian los schemas Pydantic, este archivo debe sincronizarse
 * manualmente hasta que tengamos generación automática (próximo: openapi-ts
 * o pydantic2typescript cuando exista apps/api).
 */

export interface EvidenceSpan {
  claim: string;
  source_page: number;
  source_text: string;
}

export interface LabResult {
  name: string;
  value: string;
  unit: string | null;
  date: string | null; // ISO YYYY-MM-DD
  abnormal: boolean | null;
}

export interface ObstetricSummary {
  patient_age: number | null;
  gestational_age_weeks: number | null;
  fum: string | null; // ISO YYYY-MM-DD
  fpp: string | null; // ISO YYYY-MM-DD
  active_problems: string[];
  risk_factors: string[];
  lab_results: LabResult[];
  notes_summary: string;
  confidence_score: number;
  evidence_spans: EvidenceSpan[];
}
