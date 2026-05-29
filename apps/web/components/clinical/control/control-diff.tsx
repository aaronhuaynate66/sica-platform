"use client";

import { Minus, Plus } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { ObstetricSummary } from "@/lib/types/obstetric-summary";

interface ControlDiffProps {
  a: ObstetricSummary;
  b: ObstetricSummary;
  labelA: string;
  labelB: string;
}

/**
 * Diff visual de dos ObstetricSummary.
 *
 * - Listas (active_problems, risk_factors): muestra qué se agregó (B vs A)
 *   y qué desapareció (estaba en A, ya no en B).
 * - Labs: agrupa por nombre y muestra ambos valores lado a lado, marcando
 *   nuevos/desaparecidos.
 * - Métricas escalares: muestra delta EG y peso (si está) lado a lado.
 */
export function ControlDiff({ a, b, labelA, labelB }: ControlDiffProps) {
  const probAddedSet = setDiff(b.active_problems, a.active_problems);
  const probRemovedSet = setDiff(a.active_problems, b.active_problems);
  const riskAddedSet = setDiff(b.risk_factors, a.risk_factors);
  const riskRemovedSet = setDiff(a.risk_factors, b.risk_factors);
  const labDiff = diffLabs(a.lab_results, b.lab_results);

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-5">
          <h3 className="mb-3 text-sm font-medium">Evolución gestacional</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
            <ScalarPair
              label="EG"
              a={a.gestational_age_weeks != null ? `${a.gestational_age_weeks.toFixed(1)} sem` : "—"}
              b={b.gestational_age_weeks != null ? `${b.gestational_age_weeks.toFixed(1)} sem` : "—"}
              delta={
                a.gestational_age_weeks != null && b.gestational_age_weeks != null
                  ? `+${(b.gestational_age_weeks - a.gestational_age_weeks).toFixed(1)} sem`
                  : null
              }
            />
            <ScalarPair
              label="Confianza"
              a={`${(a.confidence_score * 100).toFixed(0)}%`}
              b={`${(b.confidence_score * 100).toFixed(0)}%`}
              delta={null}
            />
            <ScalarPair
              label="Problemas activos"
              a={String(a.active_problems.length)}
              b={String(b.active_problems.length)}
              delta={null}
            />
          </dl>
        </CardContent>
      </Card>

      <DiffListCard
        title="Cambios en problemas activos"
        added={probAddedSet}
        removed={probRemovedSet}
        kept={a.active_problems.filter((p) => !probRemovedSet.has(p))}
        labelA={labelA}
        labelB={labelB}
      />
      <DiffListCard
        title="Cambios en factores de riesgo"
        added={riskAddedSet}
        removed={riskRemovedSet}
        kept={a.risk_factors.filter((r) => !riskRemovedSet.has(r))}
        labelA={labelA}
        labelB={labelB}
      />

      {labDiff.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-3 text-sm font-medium">Evolución de laboratorios</h3>
            <div className="space-y-2">
              {labDiff.map((row) => (
                <div
                  key={row.name}
                  className="flex items-center gap-3 rounded-md border border-border bg-card/40 p-3 text-sm"
                >
                  <span className="flex-1 font-medium">{row.name}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {row.valueA ?? "—"}
                    {row.valueA && row.unitA ? ` ${row.unitA}` : ""}
                  </span>
                  <span className="text-muted-foreground">→</span>
                  <span className="font-mono text-xs">
                    {row.valueB ?? "—"}
                    {row.valueB && row.unitB ? ` ${row.unitB}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function setDiff(target: string[], reference: string[]): Set<string> {
  const refSet = new Set(reference);
  const out = new Set<string>();
  for (const t of target) {
    if (!refSet.has(t)) out.add(t);
  }
  return out;
}

function ScalarPair({
  label,
  a,
  b,
  delta,
}: {
  label: string;
  a: string;
  b: string;
  delta: string | null;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 flex items-baseline gap-2 text-sm font-medium">
        <span>{a}</span>
        <span className="text-muted-foreground">→</span>
        <span>{b}</span>
        {delta && (
          <span className="ml-1 rounded bg-clinical-blue/10 px-1.5 py-0.5 text-[10px] font-mono text-clinical-blue">
            {delta}
          </span>
        )}
      </dd>
    </div>
  );
}

function DiffListCard({
  title,
  added,
  removed,
  kept,
  labelA,
  labelB,
}: {
  title: string;
  added: Set<string>;
  removed: Set<string>;
  kept: string[];
  labelA: string;
  labelB: string;
}) {
  const hasChanges = added.size > 0 || removed.size > 0;
  return (
    <Card>
      <CardContent className="p-5">
        <h3 className="mb-3 text-sm font-medium">{title}</h3>
        {!hasChanges && kept.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Sin items en ambos controles.
          </p>
        )}
        {!hasChanges && kept.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Sin cambios entre {labelA} y {labelB}.
          </p>
        )}
        {removed.size > 0 && (
          <div className="mb-3">
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
              Estaba en {labelA}, ya no en {labelB}
            </p>
            <ul className="space-y-1">
              {[...removed].map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-1.5 text-sm"
                >
                  <Minus className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {added.size > 0 && (
          <div>
            <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
              Nuevo en {labelB}
            </p>
            <ul className="space-y-1">
              {[...added].map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/5 px-3 py-1.5 text-sm"
                >
                  <Plus className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface LabDiffRow {
  name: string;
  valueA: string | null;
  unitA: string | null;
  valueB: string | null;
  unitB: string | null;
}

function diffLabs(
  a: ObstetricSummary["lab_results"],
  b: ObstetricSummary["lab_results"]
): LabDiffRow[] {
  const byName = new Map<string, LabDiffRow>();
  for (const lab of a) {
    byName.set(lab.name, {
      name: lab.name,
      valueA: lab.value,
      unitA: lab.unit,
      valueB: null,
      unitB: null,
    });
  }
  for (const lab of b) {
    const existing = byName.get(lab.name);
    if (existing) {
      existing.valueB = lab.value;
      existing.unitB = lab.unit;
    } else {
      byName.set(lab.name, {
        name: lab.name,
        valueA: null,
        unitA: null,
        valueB: lab.value,
        unitB: lab.unit,
      });
    }
  }
  return [...byName.values()].sort((x, y) => x.name.localeCompare(y.name));
}
