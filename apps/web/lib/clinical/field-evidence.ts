/**
 * Mapeo de campo clínico → filtro de EvidenceSpans.
 *
 * El schema ObstetricSummary entrega `evidence_spans: EvidenceSpan[]` como
 * un array plano — cada span tiene un campo `claim` que describe a qué
 * hecho refiere. Esta función filtra los spans relevantes para un campo
 * específico de la UI por palabras-clave del claim.
 *
 * En el futuro (R1+) el orquestador puede entregar evidencia ya agrupada
 * por campo; este helper queda como capa de adaptación retrocompatible.
 */

import type { EvidenceSpan } from "@/lib/types/obstetric-summary";

export type ClinicalField =
  | "patient_age"
  | "gestational_age_weeks"
  | "fum"
  | "fpp"
  | "active_problems"
  | "risk_factors"
  | "labs"
  | "plan";

const KEYWORDS: Record<ClinicalField, string[]> = {
  patient_age: ["edad"],
  gestational_age_weeks: ["eg", "semanas", "edad gestacional"],
  fum: ["fum", "última menstruación"],
  fpp: ["fpp", "probable de parto"],
  active_problems: [
    "anemia",
    "cesárea",
    "problema",
    "hipertensi",
    "diabetes",
    "rpm",
    "ruptura",
    "gemelar",
    "preeclampsia",
    "plaquetopenia",
    "proteinuria",
  ],
  risk_factors: ["riesgo", "previa", "antecedente"],
  labs: [
    "hemoglobina",
    "tsh",
    "glucosa",
    "hiv",
    "sífilis",
    "laboratorio",
    "plaquetas",
    "ferritina",
    "creatinina",
    "ast",
    "alt",
    "hba1c",
    "hematocrito",
  ],
  plan: ["plan", "programada", "manejo", "sulfato de magnesio", "control"],
};

export function evidenceFor(
  spans: EvidenceSpan[],
  field: ClinicalField,
  extraKeywords: string[] = [],
): EvidenceSpan[] {
  const kws = [...KEYWORDS[field], ...extraKeywords].map((k) => k.toLowerCase());
  return spans.filter((s) => {
    const claim = s.claim.toLowerCase();
    return kws.some((kw) => claim.includes(kw));
  });
}

/**
 * Filtra spans que mencionen el nombre exacto de un item (lab analito,
 * problema, etc.). Útil para vincular un solo item del array a su evidencia.
 */
export function evidenceForItem(
  spans: EvidenceSpan[],
  itemName: string,
): EvidenceSpan[] {
  const needle = itemName.toLowerCase();
  return spans.filter((s) => s.claim.toLowerCase().includes(needle));
}
