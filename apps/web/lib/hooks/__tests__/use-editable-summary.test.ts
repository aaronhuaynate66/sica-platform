import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ObstetricSummary } from "@/lib/types/obstetric-summary";
import {
  getByPath,
  setByPath,
  useEditableSummary,
} from "../use-editable-summary";

const FIXTURE: ObstetricSummary = {
  patient_age: 32,
  gestational_age_weeks: 28.3,
  fum: "2025-09-15",
  fpp: "2026-06-22",
  active_problems: ["Anemia leve gestacional", "Cesárea previa (2022)"],
  risk_factors: [],
  lab_results: [],
  notes_summary: "Original notes.",
  confidence_score: 0.95,
  evidence_spans: [],
};

describe("setByPath / getByPath", () => {
  it("sets a top-level key immutably", () => {
    const next = setByPath({ a: 1, b: 2 }, "a", 99) as Record<string, number>;
    expect(next).toEqual({ a: 99, b: 2 });
  });

  it("sets a nested array index immutably", () => {
    const next = setByPath({ xs: ["a", "b", "c"] }, "xs.1", "Z") as {
      xs: string[];
    };
    expect(next.xs).toEqual(["a", "Z", "c"]);
  });

  it("getByPath retrieves nested values", () => {
    expect(getByPath({ a: { b: 7 } }, "a.b")).toBe(7);
    expect(getByPath({ xs: [10, 20] }, "xs.1")).toBe(20);
  });

  it("getByPath returns undefined for missing path", () => {
    expect(getByPath({}, "a.b.c")).toBeUndefined();
  });
});

describe("useEditableSummary", () => {
  it("initial state: no edits", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    expect(result.current.hasEdits).toBe(false);
    expect(result.current.editedFields).toEqual([]);
    expect(result.current.summary.patient_age).toBe(32);
  });

  it("editField updates the summary and marks hasEdits", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    act(() => result.current.editField("patient_age", 45));
    expect(result.current.summary.patient_age).toBe(45);
    expect(result.current.hasEdits).toBe(true);
    expect(result.current.editedFields).toContain("patient_age");
    expect(result.current.edits[0]).toEqual({
      path: "patient_age",
      original: 32,
      current: 45,
    });
  });

  it("editField on array index updates only that item", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    act(() =>
      result.current.editField("active_problems.0", "Anemia severa ferropénica"),
    );
    expect(result.current.summary.active_problems[0]).toBe(
      "Anemia severa ferropénica",
    );
    expect(result.current.summary.active_problems[1]).toBe("Cesárea previa (2022)");
  });

  it("resetField reverts a single field but keeps other edits", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    act(() => {
      result.current.editField("patient_age", 45);
      result.current.editField("notes_summary", "Edited notes.");
    });
    expect(result.current.hasEdits).toBe(true);

    act(() => result.current.resetField("patient_age"));
    expect(result.current.summary.patient_age).toBe(32);
    expect(result.current.summary.notes_summary).toBe("Edited notes.");
    expect(result.current.editedFields).toEqual(["notes_summary"]);
  });

  it("resetAll clears every edit", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    act(() => {
      result.current.editField("patient_age", 99);
      result.current.editField("active_problems.0", "X");
    });
    expect(result.current.hasEdits).toBe(true);

    act(() => result.current.resetAll());
    expect(result.current.hasEdits).toBe(false);
    expect(result.current.summary).toEqual(FIXTURE);
  });

  it("editField with value equal to original is treated as no-op (untracked)", () => {
    const { result } = renderHook(() => useEditableSummary(FIXTURE));
    act(() => result.current.editField("patient_age", 45));
    act(() => result.current.editField("patient_age", 32)); // back to original
    expect(result.current.hasEdits).toBe(false);
  });
});
