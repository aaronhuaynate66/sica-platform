"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  Baby,
  CalendarDays,
  Users,
  Search,
  TriangleAlert,
} from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { mockPatients, type RiskLevel } from "@/lib/mock-data/patients";
import { cn } from "@/lib/utils";

type RiskFilter = "all" | RiskLevel;
type SpecialtyFilter = "all" | "obstetricia" | "neonatologia" | "pediatria";
type WeekFilter = "all" | "t1" | "t2" | "t3";

function riskColor(level: RiskLevel) {
  switch (level) {
    case "ok":
      return "text-confirm-green border-confirm-green/40";
    case "warn":
      return "text-warn-yellow border-warn-yellow/40";
    case "risk":
      return "text-risk-red border-risk-red/40";
  }
}

function formatGA(weeks: number): string {
  if (weeks === 0) return "—";
  const w = Math.floor(weeks);
  const days = Math.round((weeks - w) * 10);
  return `${w}s ${days}d`;
}

function weekInTrimester(weeks: number, t: WeekFilter): boolean {
  if (t === "all") return true;
  if (t === "t1") return weeks > 0 && weeks <= 13;
  if (t === "t2") return weeks > 13 && weeks <= 27;
  if (t === "t3") return weeks > 27;
  return true;
}

export default function DashboardPage() {
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [specialty, setSpecialty] = useState<SpecialtyFilter>("all");
  const [trimester, setTrimester] = useState<WeekFilter>("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return mockPatients.filter((p) => {
      if (riskFilter !== "all" && p.risk !== riskFilter) return false;
      if (specialty !== "all" && p.specialty !== specialty) return false;
      if (!weekInTrimester(p.gaWeeks, trimester)) return false;
      if (search && !p.name.toLowerCase().includes(search.toLowerCase()))
        return false;
      return true;
    });
  }, [riskFilter, specialty, trimester, search]);

  // KPIs (calculados sobre TODO el conjunto, no filtrado)
  const total = mockPatients.length;
  const obstetric = mockPatients.filter((p) => p.specialty === "obstetricia").length;
  const visitsThisWeek = mockPatients.filter((p) => {
    if (!p.nextVisit) return false;
    const next = new Date(p.nextVisit);
    const today = new Date("2026-05-21");
    const diff = (next.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 7;
  }).length;
  const criticalAlerts = mockPatients.filter((p) => p.risk === "risk").length;
  const gapsDetected = mockPatients.filter((p) => p.risk !== "ok").length;

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-muted/20 px-6 py-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Dashboard · Clínica Demo
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Vista de operación clínica. Tiempo real sobre cohort sintético.
            </p>
          </div>
          <Badge
            variant="outline"
            className="border-warn-yellow/50 text-warn-yellow font-mono text-[10px]"
          >
            DEMO DATA · 10 pacientes sintéticos
          </Badge>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Kpi
            icon={Users}
            label="Gestantes activas"
            value={obstetric}
            sublabel={`${total} pacientes totales`}
          />
          <Kpi
            icon={CalendarDays}
            label="Próximos 7 días"
            value={visitsThisWeek}
            sublabel="Controles programados"
          />
          <Kpi
            icon={AlertCircle}
            label="Alertas críticas"
            value={criticalAlerts}
            sublabel="Riesgo alto identificado"
            tone="risk"
          />
          <Kpi
            icon={TriangleAlert}
            label="Brechas detectadas"
            value={gapsDetected}
            sublabel="Atención o riesgo"
            tone="warn"
          />
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-8"
            />
          </div>
          <Select value={riskFilter} onValueChange={(v) => setRiskFilter(v as RiskFilter)}>
            <SelectTrigger className="h-8 w-40">
              <SelectValue placeholder="Riesgo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los riesgos</SelectItem>
              <SelectItem value="ok">Normal</SelectItem>
              <SelectItem value="warn">Atención</SelectItem>
              <SelectItem value="risk">Riesgo alto</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={specialty}
            onValueChange={(v) => setSpecialty(v as SpecialtyFilter)}
          >
            <SelectTrigger className="h-8 w-44">
              <SelectValue placeholder="Especialidad" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las especialidades</SelectItem>
              <SelectItem value="obstetricia">Obstetricia</SelectItem>
              <SelectItem value="neonatologia">Neonatología</SelectItem>
              <SelectItem value="pediatria">Pediatría</SelectItem>
            </SelectContent>
          </Select>
          <Select value={trimester} onValueChange={(v) => setTrimester(v as WeekFilter)}>
            <SelectTrigger className="h-8 w-40">
              <SelectValue placeholder="Trimestre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="t1">T1 (1–13)</SelectItem>
              <SelectItem value="t2">T2 (14–27)</SelectItem>
              <SelectItem value="t3">T3 (28–40)</SelectItem>
            </SelectContent>
          </Select>
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">
            {filtered.length} de {total}
          </span>
        </div>

        {/* Tabla */}
        <div className="rounded-md border border-border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-20 font-mono text-[10px] uppercase tracking-wider">
                  ID
                </TableHead>
                <TableHead className="font-mono text-[10px] uppercase tracking-wider">
                  Paciente
                </TableHead>
                <TableHead className="w-20 font-mono text-[10px] uppercase tracking-wider">
                  Edad
                </TableHead>
                <TableHead className="w-20 font-mono text-[10px] uppercase tracking-wider">
                  EG
                </TableHead>
                <TableHead className="font-mono text-[10px] uppercase tracking-wider">
                  Riesgo
                </TableHead>
                <TableHead className="font-mono text-[10px] uppercase tracking-wider">
                  Último
                </TableHead>
                <TableHead className="font-mono text-[10px] uppercase tracking-wider">
                  Próximo
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center text-sm text-muted-foreground py-8"
                  >
                    Sin pacientes que coincidan con los filtros.
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((p) => (
                  <TableRow key={p.id} className="text-xs">
                    <TableCell className="font-mono text-muted-foreground">
                      {p.id}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {p.specialty === "neonatologia" && (
                          <Baby className="size-3 text-clinical-blue" />
                        )}
                        <span className="font-medium">{p.name}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-0.5">
                        {p.riskReason}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {p.age}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {formatGA(p.gaWeeks)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[10px] font-normal",
                          riskColor(p.risk)
                        )}
                      >
                        {p.risk === "ok"
                          ? "normal"
                          : p.risk === "warn"
                            ? "atención"
                            : "riesgo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono tabular-nums text-muted-foreground">
                      {p.lastVisit}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {p.nextVisit ?? "—"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  sublabel,
  tone,
}: {
  icon: typeof Users;
  label: string;
  value: number;
  sublabel?: string;
  tone?: "warn" | "risk";
}) {
  return (
    <Card>
      <CardHeader className="pb-1 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-normal">
          {label}
        </CardTitle>
        <Icon
          className={cn(
            "size-3.5",
            tone === "risk" && "text-risk-red",
            tone === "warn" && "text-warn-yellow",
            !tone && "text-muted-foreground"
          )}
        />
      </CardHeader>
      <CardContent>
        <div className="font-mono text-2xl font-semibold tabular-nums">
          {value}
        </div>
        {sublabel && (
          <p className="text-[10px] text-muted-foreground mt-0.5">{sublabel}</p>
        )}
      </CardContent>
    </Card>
  );
}
