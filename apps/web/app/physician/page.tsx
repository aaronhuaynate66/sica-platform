"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  Baby,
  Calendar,
  Check,
  ChevronDown,
  Edit3,
  FileSearch,
  Keyboard,
  Stethoscope,
  TriangleAlert,
  X,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ConfidenceBar } from "@/components/clinical/confidence-bar";
import { cn } from "@/lib/utils";
import {
  currentPatient,
  physicianTasks,
  type PhysicianTask,
  type SuggestionAction,
} from "@/lib/mock-data/physician";

function priorityBadge(priority: PhysicianTask["priority"]) {
  switch (priority) {
    case "high":
      return "border-risk-red/40 text-risk-red";
    case "med":
      return "border-warn-yellow/40 text-warn-yellow";
    case "low":
      return "border-confirm-green/40 text-confirm-green";
  }
}

function priorityLabel(priority: PhysicianTask["priority"]) {
  switch (priority) {
    case "high":
      return "alta";
    case "med":
      return "media";
    case "low":
      return "baja";
  }
}

function statusLabel(status: PhysicianTask["status"]) {
  switch (status) {
    case "pending":
      return "pendiente";
    case "in_review":
      return "en revisión";
    case "done":
      return "completada";
  }
}

export default function PhysicianPage() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [suggestionStates, setSuggestionStates] = useState<
    Record<string, SuggestionAction | undefined>
  >({});

  const selected = physicianTasks[selectedIdx];

  const handleAction = useCallback(
    (suggestionId: string, action: SuggestionAction) => {
      setSuggestionStates((prev) => ({ ...prev, [suggestionId]: action }));
    },
    []
  );

  // Keyboard navigation
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // ignore if user is typing in an input
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }
      if (e.key === "j") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, physicianTasks.length - 1));
      } else if (e.key === "k") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        // simulate "open" — currently just keeps current selected
        // could open detailed sheet in future
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const sortedTimeline = useMemo(
    () => [...currentPatient.timeline].sort((a, b) => a.week - b.week),
    []
  );

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-muted/20 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              Panel del médico
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Vista densa para revisión rápida. Modo asistivo · cada acción
              requiere confirmación humana.
            </p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
            <Keyboard className="size-3" />
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">J</kbd>
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">K</kbd>
            <span>navegar</span>
            <span className="opacity-50">·</span>
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">Enter</kbd>
            <span>abrir</span>
            <span className="opacity-50">·</span>
            <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">E</kbd>
            <span>editar</span>
          </div>
        </div>
      </div>

      {/* Grid 3 cols: left (tasks) | center (patient) | right (suggestions) */}
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[300px_1fr_360px] min-h-[calc(100vh-8rem)]">
        {/* LEFT — Tasks */}
        <aside className="border-r border-border overflow-y-auto">
          <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-3 py-2 flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              Cola de revisión
            </span>
            <Badge variant="outline" className="font-mono text-[10px]">
              {physicianTasks.length}
            </Badge>
          </div>
          <ul>
            {physicianTasks.map((task, idx) => {
              const isSelected = idx === selectedIdx;
              return (
                <li key={task.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedIdx(idx)}
                    className={cn(
                      "w-full text-left px-3 py-2.5 border-b border-border/60 hover:bg-muted/40 transition-colors",
                      isSelected && "bg-muted border-l-2 border-l-clinical-blue"
                    )}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {task.id}
                      </span>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[9px] font-normal h-4",
                          priorityBadge(task.priority)
                        )}
                      >
                        {priorityLabel(task.priority)}
                      </Badge>
                    </div>
                    <div className="text-sm font-medium leading-tight">
                      {task.title}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5 truncate">
                      {task.patientName} · {task.subtitle}
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground">
                      <span>{statusLabel(task.status)}</span>
                      {task.patientGA > 0 && (
                        <>
                          <span className="opacity-50">·</span>
                          <span className="font-mono tabular-nums">
                            {Math.floor(task.patientGA)}s
                          </span>
                        </>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* CENTER — Patient context */}
        <main className="overflow-y-auto p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Stethoscope className="size-4 text-clinical-blue" />
                <h2 className="text-lg font-semibold">{currentPatient.name}</h2>
                <Badge variant="outline" className="font-mono text-[10px]">
                  {currentPatient.id}
                </Badge>
              </div>
              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                <span>{currentPatient.age} años</span>
                <span className="opacity-50">·</span>
                <span className="font-mono tabular-nums">
                  EG {Math.floor(currentPatient.gaWeeks)}s{" "}
                  {Math.round((currentPatient.gaWeeks - Math.floor(currentPatient.gaWeeks)) * 10)}d
                </span>
                <span className="opacity-50">·</span>
                <span>G2P1</span>
              </div>
            </div>
            <Button variant="outline" size="sm" className="gap-1.5">
              <FileSearch className="size-3.5" />
              Ver historia
            </Button>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-normal">
                Resumen ejecutivo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">
                {currentPatient.notesSummary}
              </p>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-normal flex items-center gap-2">
                  <AlertCircle className="size-3.5 text-warn-yellow" />
                  Problemas activos
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-wrap gap-1.5">
                  {currentPatient.activeProblems.map((p) => (
                    <li key={p}>
                      <Badge variant="secondary" className="font-normal text-xs">
                        {p}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-normal flex items-center gap-2">
                  <TriangleAlert className="size-3.5 text-warn-yellow" />
                  Factores de riesgo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-wrap gap-1.5">
                  {currentPatient.riskFactors.map((r) => (
                    <li key={r}>
                      <Badge
                        variant="outline"
                        className="border-warn-yellow/40 text-warn-yellow font-normal text-xs"
                      >
                        {r}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Mini timeline */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-normal flex items-center gap-2">
                <Calendar className="size-3.5 text-clinical-blue" />
                Línea de tiempo (últimos 4 eventos)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-2">
                {sortedTimeline.map((ev) => (
                  <li
                    key={ev.id}
                    className="flex items-start gap-2 text-xs"
                  >
                    <span className="font-mono tabular-nums w-12 text-muted-foreground shrink-0">
                      sem {ev.week}
                    </span>
                    <span className="flex-1">{ev.title}</span>
                    <Baby
                      className={cn(
                        "size-3 shrink-0",
                        ev.riskLevel === "ok" && "text-confirm-green",
                        ev.riskLevel === "warn" && "text-warn-yellow",
                        ev.riskLevel === "risk" && "text-risk-red"
                      )}
                    />
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </main>

        {/* RIGHT — Suggestions */}
        <aside className="border-l border-border overflow-y-auto">
          <div className="sticky top-0 z-10 bg-background/95 backdrop-blur border-b border-border px-3 py-2 flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              Sugerencias SICA
            </span>
            <Badge variant="outline" className="font-mono text-[10px]">
              {currentPatient.suggestions.length}
            </Badge>
          </div>
          <ul className="p-3 space-y-3">
            {currentPatient.suggestions.map((s) => {
              const state = suggestionStates[s.id];
              return (
                <li
                  key={s.id}
                  className={cn(
                    "rounded-md border border-border bg-card p-3 transition-opacity",
                    state === "reject" && "opacity-50"
                  )}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="text-sm font-medium leading-tight">
                      {s.title}
                    </h3>
                    {state && (
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[9px] font-normal h-4 shrink-0",
                          state === "accept" && "border-confirm-green/40 text-confirm-green",
                          state === "edit" && "border-warn-yellow/40 text-warn-yellow",
                          state === "reject" && "border-risk-red/40 text-risk-red"
                        )}
                      >
                        {state === "accept"
                          ? "aceptada"
                          : state === "edit"
                            ? "editada"
                            : "rechazada"}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mb-2 leading-relaxed">
                    {s.rationale}
                  </p>
                  <div className="rounded bg-muted/40 px-2 py-1.5 mb-3">
                    <p className="text-[10px] font-mono text-muted-foreground flex items-start gap-1">
                      <ChevronDown className="size-2.5 mt-0.5 shrink-0" />
                      <span className="leading-snug">{s.evidence}</span>
                    </p>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <ConfidenceBar value={s.confidence} />
                    </div>
                  </div>
                  <Separator className="my-2.5" />
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="xs"
                      className="gap-1"
                      onClick={() => handleAction(s.id, "reject")}
                      disabled={state === "reject"}
                    >
                      <X className="size-3" />
                      Rechazar
                    </Button>
                    <Button
                      variant="ghost"
                      size="xs"
                      className="gap-1"
                      onClick={() => handleAction(s.id, "edit")}
                      disabled={state === "edit"}
                    >
                      <Edit3 className="size-3" />
                      Editar
                    </Button>
                    <Button
                      variant="default"
                      size="xs"
                      className="gap-1"
                      onClick={() => handleAction(s.id, "accept")}
                      disabled={state === "accept"}
                    >
                      <Check className="size-3" />
                      Aceptar
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="px-3 pb-4 text-[10px] text-muted-foreground flex items-center gap-1">
            <ArrowRight className="size-3" />
            <span>
              Tarea actual: <span className="text-foreground">{selected.title}</span>
            </span>
          </div>
        </aside>
      </div>
    </div>
  );
}
