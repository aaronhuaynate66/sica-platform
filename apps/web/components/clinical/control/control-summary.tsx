"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ObstetricSummary } from "@/lib/types/obstetric-summary";
import { formatDateEs } from "@/lib/utils/dates";

interface ControlSummaryProps {
  summary: ObstetricSummary;
}

export function ControlSummary({ summary }: ControlSummaryProps) {
  return (
    <div className="space-y-4">
      <DemographicsCard summary={summary} />
      <ProblemsCard
        title="Problemas activos"
        items={summary.active_problems}
        empty="Sin problemas activos consignados"
      />
      <ProblemsCard
        title="Factores de riesgo"
        items={summary.risk_factors}
        empty="Sin factores de riesgo consignados"
      />
      {summary.lab_results.length > 0 && <LabsCard summary={summary} />}
      {summary.notes_summary && <NotesCard summary={summary} />}
      <EvidenceCard summary={summary} />
    </div>
  );
}

function DemographicsCard({ summary }: { summary: ObstetricSummary }) {
  const rows: Array<[string, string]> = [
    ["Edad", summary.patient_age != null ? `${summary.patient_age} años` : "—"],
    [
      "Edad gestacional",
      summary.gestational_age_weeks != null
        ? `${summary.gestational_age_weeks.toFixed(1)} sem`
        : "—",
    ],
    ["FUM", formatDateEs(summary.fum)],
    ["FPP", formatDateEs(summary.fpp)],
    [
      "Confianza extracción",
      `${(summary.confidence_score * 100).toFixed(0)}%`,
    ],
  ];
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium">Datos del control</h3>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-5">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
              </dt>
              <dd className="mt-0.5 text-sm font-medium">{value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}

function ProblemsCard({
  title,
  items,
  empty,
}: {
  title: string;
  items: string[];
  empty: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium">{title}</h3>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{empty}</p>
        ) : (
          <ul className="space-y-1.5">
            {items.map((p, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm leading-relaxed"
              >
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-clinical-blue" />
                <span>{p}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function LabsCard({ summary }: { summary: ObstetricSummary }) {
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium">Laboratorios</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Test</TableHead>
              <TableHead>Valor</TableHead>
              <TableHead>Unidad</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {summary.lab_results.map((l, i) => (
              <TableRow key={i}>
                <TableCell className="font-medium">{l.name}</TableCell>
                <TableCell className="font-mono text-sm">{l.value}</TableCell>
                <TableCell className="text-muted-foreground">
                  {l.unit ?? "—"}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDateEs(l.date)}
                </TableCell>
                <TableCell>
                  {l.abnormal === true && (
                    <Badge variant="destructive">Anormal</Badge>
                  )}
                  {l.abnormal === false && (
                    <Badge variant="secondary">Normal</Badge>
                  )}
                  {l.abnormal == null && (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function NotesCard({ summary }: { summary: ObstetricSummary }) {
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium">Resumen narrativo</h3>
        <p className="whitespace-pre-line text-sm leading-relaxed">
          {summary.notes_summary}
        </p>
      </CardContent>
    </Card>
  );
}

function EvidenceCard({ summary }: { summary: ObstetricSummary }) {
  const [open, setOpen] = useState(false);
  if (summary.evidence_spans.length === 0) return null;

  return (
    <Card>
      <CardContent className="p-5">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between text-sm font-medium"
        >
          <span>
            Evidencia trazable
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              ({summary.evidence_spans.length} spans)
            </span>
          </span>
          {open ? (
            <ChevronDown className="size-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-4 text-muted-foreground" />
          )}
        </button>
        {open && (
          <ul className="mt-3 space-y-3">
            {summary.evidence_spans.map((span, i) => (
              <li
                key={i}
                className="rounded-md border border-border bg-muted/30 p-3 text-xs"
              >
                <p className="mb-1 font-medium">{span.claim}</p>
                <p className="font-mono text-muted-foreground">
                  <span className="rounded bg-muted px-1 py-0.5">
                    p. {span.source_page}
                  </span>{" "}
                  «{span.source_text}»
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
