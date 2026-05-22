import {
  Activity,
  Calendar,
  CheckCircle2,
  FileText,
  FlaskConical,
  Stethoscope,
  TriangleAlert,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceBar } from "@/components/clinical/confidence-bar";
import { EditableField } from "@/components/clinical/editable-field";
import { EvidenceModal } from "@/components/clinical/evidence-modal";
import { Separator } from "@/components/ui/separator";
import { evidenceFor, evidenceForItem } from "@/lib/clinical/field-evidence";
import type { ObstetricSummary } from "@/lib/api/types";

function formatGA(weeks: number | null): string {
  if (weeks === null) return "—";
  const w = Math.floor(weeks);
  const days = Math.round((weeks - w) * 10);
  return `${w}s ${days}d`;
}

function formatDateEs(iso: string | null): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
}

interface SummaryViewProps {
  summary: ObstetricSummary;
  pdfPath: string | null;
  pdfLabel: string;
  origin: "demo" | "live";
  /**
   * Si se provee, los 3 campos editables (patient_age, active_problems[*],
   * notes_summary) se renderizan con `EditableField`. Si no, son sólo lectura.
   */
  editing?: {
    editField: (path: string, newValue: unknown) => void;
    resetField: (path: string) => void;
    editedFields: string[];
  };
}

export function SummaryView({
  summary,
  pdfPath,
  pdfLabel,
  origin,
  editing,
}: SummaryViewProps) {
  const spans = summary.evidence_spans;
  const isEdited = (path: string) => editing?.editedFields.includes(path) ?? false;

  return (
    <div className="grid flex-1 grid-cols-1 lg:grid-cols-[60%_40%]">
      <section className="border-r border-border bg-muted/10 flex flex-col">
        <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2">
          <div className="flex items-center gap-2">
            <FileText className="size-4 text-muted-foreground" />
            <span className="font-mono text-xs">{pdfLabel}</span>
          </div>
          <span className="font-mono text-[10px] text-muted-foreground">
            {origin === "demo" ? "DEMO · 100% sintético" : "LIVE · extracción real"}
          </span>
        </div>
        {pdfPath ? (
          <iframe
            src={pdfPath}
            title="PDF original"
            className="flex-1 w-full min-h-[60vh] bg-white"
          />
        ) : (
          <div className="flex flex-1 items-center justify-center bg-white text-xs text-muted-foreground">
            (PDF subido vive solo en memoria — no se persiste vista previa)
          </div>
        )}
        <div className="border-t border-border bg-muted/40 px-4 py-2 text-[11px] flex items-center gap-2 text-muted-foreground">
          <CheckCircle2 className="size-3.5 text-confirm-green shrink-0" />
          <span>
            <strong className="text-foreground font-medium">Trazabilidad activada</strong> — cada
            dato extraído incluye referencia al texto fuente del documento.
          </span>
        </div>
      </section>

      <section className="flex flex-col gap-4 p-4 overflow-y-auto max-h-[calc(100vh-9rem)]">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Activity className="size-4 text-clinical-blue" />
                Confianza de extracción
              </CardTitle>
              <span className="font-mono text-xs tabular-nums">
                {Math.round(summary.confidence_score * 100)}%
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <ConfidenceBar value={summary.confidence_score} />
            <p className="mt-2 text-[11px] text-muted-foreground">
              {summary.evidence_spans.length} spans de evidencia indexados desde el documento.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Calendar className="size-4 text-clinical-blue" />
              Datos gestacionales
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-2 text-sm items-center">
              <dt className="text-muted-foreground">Edad</dt>
              <dd className="font-mono tabular-nums text-right">
                {editing ? (
                  <EditableField
                    label="Edad de la paciente"
                    value={summary.patient_age ?? 0}
                    editType="number"
                    isEdited={isEdited("patient_age")}
                    onSave={(v) => editing.editField("patient_age", v)}
                    onReset={() => editing.resetField("patient_age")}
                    renderValue={(v) => <span>{v} años</span>}
                  />
                ) : (
                  <span>{summary.patient_age ?? "—"} años</span>
                )}
              </dd>
              <EvidenceModal
                evidence={evidenceFor(spans, "patient_age")}
                fieldName="Edad"
                pdfUrl={pdfPath}
              />

              <dt className="text-muted-foreground">EG actual</dt>
              <dd className="font-mono tabular-nums text-right">
                {formatGA(summary.gestational_age_weeks)}
              </dd>
              <EvidenceModal
                evidence={evidenceFor(spans, "gestational_age_weeks")}
                fieldName="Edad gestacional"
                pdfUrl={pdfPath}
              />

              <dt className="text-muted-foreground">FUM</dt>
              <dd className="font-mono tabular-nums text-right">{formatDateEs(summary.fum)}</dd>
              <EvidenceModal
                evidence={evidenceFor(spans, "fum")}
                fieldName="FUM"
                pdfUrl={pdfPath}
              />

              <dt className="text-muted-foreground">FPP</dt>
              <dd className="font-mono tabular-nums text-right">{formatDateEs(summary.fpp)}</dd>
              <EvidenceModal
                evidence={evidenceFor(spans, "fpp")}
                fieldName="FPP"
                pdfUrl={pdfPath}
              />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TriangleAlert className="size-4 text-warn-yellow" />
              Problemas activos
            </CardTitle>
            <EvidenceModal
              evidence={evidenceFor(spans, "active_problems")}
              fieldName="Problemas activos"
              pdfUrl={pdfPath}
            />
          </CardHeader>
          <CardContent>
            {summary.active_problems.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin problemas activos.</p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {summary.active_problems.map((p, idx) => {
                  const path = `active_problems.${idx}`;
                  const itemSpans = evidenceForItem(spans, p);
                  return (
                    <li
                      key={`${path}-${p}`}
                      className="flex items-center justify-between gap-2"
                    >
                      {editing ? (
                        <EditableField
                          label={`Problema activo ${idx + 1}`}
                          value={p}
                          editType="text"
                          isEdited={isEdited(path)}
                          onSave={(v) => editing.editField(path, v)}
                          onReset={() => editing.resetField(path)}
                          renderValue={(v) => (
                            <Badge variant="secondary" className="font-normal">
                              {v}
                            </Badge>
                          )}
                        />
                      ) : (
                        <Badge variant="secondary" className="font-normal">
                          {p}
                        </Badge>
                      )}
                      <EvidenceModal evidence={itemSpans} fieldName={p} pdfUrl={pdfPath} />
                    </li>
                  );
                })}
              </ul>
            )}
            {summary.risk_factors.length > 0 && (
              <>
                <Separator className="my-3" />
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
                  Factores de riesgo
                </p>
                <ul className="flex flex-wrap gap-1.5">
                  {summary.risk_factors.map((r) => (
                    <li key={r}>
                      <Badge
                        variant="outline"
                        className="border-warn-yellow/40 text-warn-yellow font-normal"
                      >
                        {r}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FlaskConical className="size-4 text-clinical-blue" />
              Laboratorios
            </CardTitle>
            <EvidenceModal
              evidence={evidenceFor(spans, "labs")}
              fieldName="Laboratorios"
              pdfUrl={pdfPath}
            />
          </CardHeader>
          <CardContent>
            {summary.lab_results.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin laboratorios.</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground text-left">
                    <th className="font-normal pb-1.5">Analito</th>
                    <th className="font-normal pb-1.5 text-right">Valor</th>
                    <th className="font-normal pb-1.5 text-right">Estado</th>
                    <th className="font-normal pb-1.5"></th>
                  </tr>
                </thead>
                <tbody className="font-mono tabular-nums">
                  {summary.lab_results.map((lab) => (
                    <tr key={lab.name} className="border-t border-border/50">
                      <td className="py-1.5 font-sans">{lab.name}</td>
                      <td className="py-1.5 text-right">
                        {lab.value}
                        {lab.unit ? ` ${lab.unit}` : ""}
                      </td>
                      <td className="py-1.5 text-right">
                        {lab.abnormal ? (
                          <Badge
                            variant="outline"
                            className="border-risk-red/40 text-risk-red font-normal text-[10px]"
                          >
                            anormal
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="border-confirm-green/40 text-confirm-green font-normal text-[10px]"
                          >
                            normal
                          </Badge>
                        )}
                      </td>
                      <td className="py-1.5 text-right">
                        <EvidenceModal
                          evidence={evidenceForItem(spans, lab.name)}
                          fieldName={lab.name}
                          pdfUrl={pdfPath}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Stethoscope className="size-4 text-clinical-blue" />
              Resumen y plan
            </CardTitle>
            <EvidenceModal
              evidence={evidenceFor(spans, "plan")}
              fieldName="Plan"
              pdfUrl={pdfPath}
            />
          </CardHeader>
          <CardContent>
            {editing ? (
              <EditableField
                label="Resumen y plan"
                value={summary.notes_summary}
                editType="textarea"
                isEdited={isEdited("notes_summary")}
                onSave={(v) => editing.editField("notes_summary", v)}
                onReset={() => editing.resetField("notes_summary")}
                renderValue={(v) => (
                  <p className="text-sm leading-relaxed text-foreground/90 inline">{v}</p>
                )}
                className="w-full items-start"
              />
            ) : (
              <p className="text-sm leading-relaxed text-foreground/90">
                {summary.notes_summary}
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
