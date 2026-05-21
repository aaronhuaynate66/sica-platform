"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  CalendarCheck,
  FlaskConical,
  Scan,
  Stethoscope,
  TriangleAlert,
} from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  type TimelineEvent,
  type TimelineEventKind,
  type TimelineEventRiskLevel,
  timelineEvents,
} from "@/lib/mock-data/timeline";

const WEEKS_TOTAL = 40;

function riskBg(level: TimelineEventRiskLevel): string {
  switch (level) {
    case "ok":
      return "bg-confirm-green";
    case "warn":
      return "bg-warn-yellow";
    case "risk":
      return "bg-risk-red";
  }
}

function riskRing(level: TimelineEventRiskLevel): string {
  switch (level) {
    case "ok":
      return "ring-confirm-green/30";
    case "warn":
      return "ring-warn-yellow/30";
    case "risk":
      return "ring-risk-red/30";
  }
}

function kindIcon(kind: TimelineEventKind) {
  switch (kind) {
    case "fum":
      return Activity;
    case "control":
      return Stethoscope;
    case "ecografia":
      return Scan;
    case "laboratorio":
      return FlaskConical;
    case "factor_riesgo":
      return TriangleAlert;
    case "plan":
      return CalendarCheck;
  }
}

function kindLabel(kind: TimelineEventKind): string {
  switch (kind) {
    case "fum":
      return "FUM";
    case "control":
      return "Control prenatal";
    case "ecografia":
      return "Ecografía";
    case "laboratorio":
      return "Laboratorio";
    case "factor_riesgo":
      return "Factor de riesgo";
    case "plan":
      return "Plan de parto";
  }
}

function formatDateEs(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export default function TimelinePage() {
  const [selected, setSelected] = useState<TimelineEvent | null>(null);

  const sortedEvents = useMemo(
    () => [...timelineEvents].sort((a, b) => a.week - b.week),
    []
  );

  const trimesterMarkers = useMemo(
    () => [
      { week: 0, label: "Sem 0" },
      { week: 13, label: "T1 → T2" },
      { week: 27, label: "T2 → T3" },
      { week: 40, label: "Término" },
    ],
    []
  );

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-muted/20 px-6 py-6">
        <h1 className="text-2xl font-semibold tracking-tight">Timeline gestacional</h1>
        <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
          Reconstrucción longitudinal del embarazo en curso. Cada marcador es
          un evento clínico inferido desde el documento original. Click para ver
          detalle.
        </p>
      </div>

      <div className="flex-1 px-6 py-8">
        {/* Leyenda */}
        <div className="flex items-center gap-4 mb-8 text-xs">
          <span className="text-muted-foreground">Estado:</span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-confirm-green" /> Normal
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-warn-yellow" /> Atención
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-risk-red" /> Riesgo identificado
          </span>
        </div>

        {/* Timeline SVG-like */}
        <div className="relative pt-12 pb-6">
          {/* Eje horizontal */}
          <div className="absolute left-0 right-0 top-[5.5rem] h-0.5 bg-border" />

          {/* Marcas de trimestres */}
          <div className="absolute left-0 right-0 top-[5.25rem] flex justify-between">
            {trimesterMarkers.map((m) => (
              <div
                key={m.week}
                className="flex flex-col items-center"
                style={{ marginLeft: m.week === 0 ? 0 : undefined }}
              >
                <span className="h-2.5 w-0.5 bg-border" />
                <span className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {m.label}
                </span>
              </div>
            ))}
          </div>

          {/* Markers */}
          <div className="relative h-12">
            {sortedEvents.map((ev) => {
              const Icon = kindIcon(ev.kind);
              const leftPct = (ev.week / WEEKS_TOTAL) * 100;
              return (
                <button
                  key={ev.id}
                  type="button"
                  onClick={() => setSelected(ev)}
                  className={cn(
                    "group absolute -translate-x-1/2 flex flex-col items-center gap-1",
                    "outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
                  )}
                  style={{ left: `${leftPct}%`, top: 0 }}
                  aria-label={`${ev.title} — semana ${ev.week}`}
                >
                  <div
                    className={cn(
                      "flex size-7 items-center justify-center rounded-full ring-4 ring-background border border-border bg-background transition-transform group-hover:scale-110",
                      riskRing(ev.riskLevel)
                    )}
                  >
                    <div
                      className={cn(
                        "flex size-5 items-center justify-center rounded-full",
                        riskBg(ev.riskLevel)
                      )}
                    >
                      <Icon className="size-3 text-background" />
                    </div>
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
                    {ev.week}s
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Lista de eventos (visión densa) */}
        <Separator className="mt-8 mb-6" />
        <div className="grid gap-2">
          {sortedEvents.map((ev) => {
            const Icon = kindIcon(ev.kind);
            return (
              <button
                key={ev.id}
                type="button"
                onClick={() => setSelected(ev)}
                className="group flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2 text-left hover:bg-muted/40 transition-colors"
              >
                <div
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full",
                    riskBg(ev.riskLevel)
                  )}
                >
                  <Icon className="size-3 text-background" />
                </div>
                <span className="font-mono text-xs text-muted-foreground tabular-nums w-12">
                  {ev.week}s
                </span>
                <span className="text-sm flex-1 truncate">{ev.title}</span>
                <span className="text-xs text-muted-foreground hidden md:inline">
                  {ev.description}
                </span>
                <Badge variant="outline" className="text-[10px] font-normal">
                  {kindLabel(ev.kind)}
                </Badge>
                <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
                  {formatDateEs(ev.date)}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Drawer / Sheet */}
      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="w-full sm:max-w-md">
          {selected && (
            <>
              <SheetHeader>
                <div className="flex items-center justify-between gap-2">
                  <SheetTitle>{selected.title}</SheetTitle>
                  <Badge variant="outline" className="font-mono">
                    sem {selected.week}
                  </Badge>
                </div>
                <SheetDescription>
                  {kindLabel(selected.kind)} · {formatDateEs(selected.date)}
                </SheetDescription>
              </SheetHeader>
              <div className="px-4 pb-6 space-y-4">
                <p className="text-sm text-foreground">{selected.description}</p>
                <Separator />
                <ul className="space-y-1.5 text-sm text-foreground/90">
                  {selected.details.map((d, idx) => (
                    <li key={idx} className="flex gap-2">
                      <span className="text-muted-foreground">·</span>
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
