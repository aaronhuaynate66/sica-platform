import { Activity, Calendar, FileText, FlaskConical, Stethoscope, TriangleAlert } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConfidenceBar } from "@/components/clinical/confidence-bar";
import { EvidenceSheet } from "@/components/clinical/evidence-sheet";
import {
  syntheticCase01PdfPath,
  syntheticCase01Summary,
} from "@/lib/fixtures";

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

export default function UploadAndExtractPage() {
  const summary = syntheticCase01Summary;

  const spansBy = (claimKeywords: string[]) =>
    summary.evidence_spans.filter((s) =>
      claimKeywords.some((kw) => s.claim.toLowerCase().includes(kw))
    );

  return (
    <div className="flex flex-col">
      {/* Hero */}
      <div className="border-b border-border bg-muted/20 px-6 py-6">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              SICA — Demo interna
            </h1>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              Carga una historia clínica obstétrica y SICA la transforma en un
              resumen estructurado con evidencia trazable. Esta demo usa{" "}
              <strong className="text-foreground">datos sintéticos</strong>; no
              hay paciente real, no hay backend conectado.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono">
              caso 01
            </Badge>
            <Badge variant="outline" className="border-warn-yellow/50 text-warn-yellow">
              sintético
            </Badge>
          </div>
        </div>
      </div>

      {/* Split layout */}
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[60%_40%]">
        {/* PDF preview */}
        <section className="border-r border-border bg-muted/10 flex flex-col">
          <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2">
            <div className="flex items-center gap-2">
              <FileText className="size-4 text-muted-foreground" />
              <span className="font-mono text-xs">synthetic_case_01.pdf</span>
            </div>
            <span className="font-mono text-[10px] text-muted-foreground">
              DEMO · 100% sintético
            </span>
          </div>
          <iframe
            src={syntheticCase01PdfPath}
            title="PDF original sintético"
            className="flex-1 w-full min-h-[70vh] bg-white"
          />
        </section>

        {/* JSON cards */}
        <section className="flex flex-col gap-4 p-4 overflow-y-auto max-h-[calc(100vh-9rem)]">
          {/* Confidence header */}
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
                {summary.evidence_spans.length} spans de evidencia indexados
                desde el documento.
              </p>
            </CardContent>
          </Card>

          {/* Demographic + gestational */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Calendar className="size-4 text-clinical-blue" />
                Datos gestacionales
              </CardTitle>
              <EvidenceSheet
                title="Evidencia · Datos gestacionales"
                spans={spansBy(["edad", "fum", "fpp", "eg"])}
              />
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <dt className="text-muted-foreground">Edad</dt>
                <dd className="font-mono tabular-nums">
                  {summary.patient_age ?? "—"} años
                </dd>
                <dt className="text-muted-foreground">EG actual</dt>
                <dd className="font-mono tabular-nums">
                  {formatGA(summary.gestational_age_weeks)}
                </dd>
                <dt className="text-muted-foreground">FUM</dt>
                <dd className="font-mono tabular-nums">
                  {formatDateEs(summary.fum)}
                </dd>
                <dt className="text-muted-foreground">FPP</dt>
                <dd className="font-mono tabular-nums">
                  {formatDateEs(summary.fpp)}
                </dd>
              </dl>
            </CardContent>
          </Card>

          {/* Active problems */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <TriangleAlert className="size-4 text-warn-yellow" />
                Problemas activos
              </CardTitle>
              <EvidenceSheet
                title="Evidencia · Problemas activos"
                spans={spansBy(["anemia", "cesárea", "problema"])}
              />
            </CardHeader>
            <CardContent>
              {summary.active_problems.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin problemas activos.</p>
              ) : (
                <ul className="flex flex-wrap gap-1.5">
                  {summary.active_problems.map((p) => (
                    <li key={p}>
                      <Badge variant="secondary" className="font-normal">
                        {p}
                      </Badge>
                    </li>
                  ))}
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

          {/* Labs */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FlaskConical className="size-4 text-clinical-blue" />
                Laboratorios
              </CardTitle>
              <EvidenceSheet
                title="Evidencia · Laboratorios"
                spans={spansBy([
                  "hemoglobina",
                  "tsh",
                  "glucosa",
                  "hiv",
                  "sífilis",
                  "laboratorio",
                ])}
              />
            </CardHeader>
            <CardContent>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground text-left">
                    <th className="font-normal pb-1.5">Analito</th>
                    <th className="font-normal pb-1.5 text-right">Valor</th>
                    <th className="font-normal pb-1.5 text-right">Estado</th>
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
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {/* Notes summary */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Stethoscope className="size-4 text-clinical-blue" />
                Resumen y plan
              </CardTitle>
              <EvidenceSheet
                title="Evidencia · Plan"
                spans={spansBy(["plan", "cesárea programada"])}
              />
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-foreground/90">
                {summary.notes_summary}
              </p>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
