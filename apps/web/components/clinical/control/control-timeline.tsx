"use client";

import Link from "next/link";
import { CalendarDays, Stethoscope } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Control } from "@/lib/types/database";
import { cn } from "@/lib/utils";
import { formatDateEs } from "@/lib/utils/dates";

interface ControlTimelineProps {
  pacienteId: string;
  controles: Control[];
}

export function ControlTimeline({ pacienteId, controles }: ControlTimelineProps) {
  if (controles.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card/40 p-8 text-center">
        <Stethoscope className="mx-auto mb-3 size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Aún no hay controles para este paciente.
        </p>
      </div>
    );
  }

  return (
    <ol className="relative space-y-4 border-l-2 border-border pl-6">
      {controles.map((c, idx) => {
        const summary = c.resumen_json;
        const isLast = idx === controles.length - 1;
        return (
          <li key={c.id} className="relative">
            <span
              className={cn(
                "absolute -left-[1.85rem] mt-1.5 size-3 rounded-full ring-4 ring-background",
                isLast ? "bg-clinical-blue" : "bg-muted-foreground/60"
              )}
              aria-hidden
            />
            <Link
              href={`/app/pacientes/${pacienteId}/controles/${c.id}`}
              className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-clinical-blue/40 hover:bg-muted/20"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <CalendarDays className="size-4 text-muted-foreground" />
                  <span className="text-sm font-medium">
                    {formatDateEs(c.fecha_control)}
                  </span>
                </div>
                {c.semanas_gestacion != null && (
                  <Badge variant="outline">
                    {c.semanas_gestacion.toFixed(1)} sem
                  </Badge>
                )}
              </div>
              {summary.active_problems && summary.active_problems.length > 0 ? (
                <ul className="space-y-0.5 text-xs text-muted-foreground">
                  {summary.active_problems.slice(0, 3).map((p, i) => (
                    <li key={i} className="line-clamp-1">
                      · {p}
                    </li>
                  ))}
                  {summary.active_problems.length > 3 && (
                    <li className="text-muted-foreground/60">
                      + {summary.active_problems.length - 3} más
                    </li>
                  )}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Sin problemas activos consignados
                </p>
              )}
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
