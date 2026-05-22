"use client";

import { EditsIndicator } from "@/components/clinical/edits-indicator";
import { SummaryView } from "@/components/clinical/summary-view";
import { useEditableSummary } from "@/lib/hooks/use-editable-summary";
import type { ObstetricSummary } from "@/lib/api/types";

interface EditableSummaryViewProps {
  initialSummary: ObstetricSummary;
  pdfPath: string | null;
  pdfLabel: string;
  origin: "demo" | "live";
}

/**
 * Wrapper sobre `SummaryView` que añade estado editable + indicador de
 * cambios. Se monta sólo cuando hay un summary disponible — eso permite
 * llamar al hook sin patrones condicionales en el caller.
 */
export function EditableSummaryView({
  initialSummary,
  pdfPath,
  pdfLabel,
  origin,
}: EditableSummaryViewProps) {
  const { summary, editField, resetField, resetAll, edits } =
    useEditableSummary(initialSummary);

  return (
    <div className="flex flex-col flex-1">
      {edits.length > 0 ? (
        <div className="border-b border-border bg-warn-yellow/5 px-6 py-2 flex justify-end">
          <EditsIndicator edits={edits} onResetAll={resetAll} />
        </div>
      ) : null}
      <SummaryView
        summary={summary}
        pdfPath={pdfPath}
        pdfLabel={pdfLabel}
        origin={origin}
        editing={{
          editField,
          resetField,
          editedFields: edits.map((e) => e.path),
        }}
      />
    </div>
  );
}
