import { describe, expect, it } from "vitest";

import type { EvidenceSpan } from "@/lib/types/obstetric-summary";
import { evidenceFor, evidenceForItem } from "../field-evidence";

const sampleSpans: EvidenceSpan[] = [
  { claim: "Edad 32 años", source_page: 1, source_text: "Edad: 32" },
  { claim: "FUM 15/09/2025", source_page: 1, source_text: "FUM 15/09/2025" },
  { claim: "EG 28 semanas 2 días", source_page: 1, source_text: "EG 28sem" },
  { claim: "Hemoglobina 10.8 g/dL", source_page: 1, source_text: "Hb 10.8" },
  { claim: "Plan cesárea programada 39 semanas", source_page: 2, source_text: "Plan: cesárea" },
];

describe("evidenceFor", () => {
  it("filters by patient_age keyword", () => {
    const result = evidenceFor(sampleSpans, "patient_age");
    expect(result).toHaveLength(1);
    expect(result[0].claim).toContain("Edad");
  });

  it("matches gestational_age_weeks via multiple keywords", () => {
    const result = evidenceFor(sampleSpans, "gestational_age_weeks");
    expect(result.some((s) => s.claim.includes("EG"))).toBe(true);
  });

  it("returns empty array when no claim matches", () => {
    const result = evidenceFor(sampleSpans, "fpp"); // ningún claim menciona FPP
    expect(result).toEqual([]);
  });

  it("accepts extra keywords to broaden the filter", () => {
    const result = evidenceFor(sampleSpans, "plan", ["cesárea programada"]);
    expect(result).toHaveLength(1);
    expect(result[0].source_page).toBe(2);
  });
});

describe("evidenceForItem", () => {
  it("returns spans whose claim mentions the item name", () => {
    const result = evidenceForItem(sampleSpans, "Hemoglobina");
    expect(result).toHaveLength(1);
    expect(result[0].claim).toContain("Hemoglobina");
  });

  it("is case-insensitive", () => {
    const result = evidenceForItem(sampleSpans, "HEMOGLOBINA");
    expect(result).toHaveLength(1);
  });

  it("returns empty array for unknown item", () => {
    const result = evidenceForItem(sampleSpans, "Triglycerides");
    expect(result).toEqual([]);
  });
});
