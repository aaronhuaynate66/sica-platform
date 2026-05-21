/**
 * Mock data para la vista del médico (Vista 4).
 *
 * DATOS SINTÉTICOS. No es paciente real.
 *
 * Modela:
 * - tareas pendientes del médico (cola de revisión)
 * - sugerencias del sistema con confidence + evidence (asistivas)
 */

import type { TimelineEvent } from "./timeline";
import { timelineEvents } from "./timeline";

export type TaskStatus = "pending" | "in_review" | "done";
export type TaskKind =
  | "revisar_resumen"
  | "validar_lab"
  | "alerta"
  | "handoff"
  | "agendar";

export interface PhysicianTask {
  id: string;
  patientId: string;
  patientName: string;
  patientGA: number;
  kind: TaskKind;
  title: string;
  subtitle: string;
  status: TaskStatus;
  priority: "low" | "med" | "high";
  riskLevel: "ok" | "warn" | "risk";
}

export type SuggestionAction = "accept" | "edit" | "reject";

export interface PhysicianSuggestion {
  id: string;
  title: string;
  rationale: string;
  evidence: string;
  confidence: number; // 0..1
  category: "documentacion" | "alerta" | "preparacion" | "seguimiento";
}

export interface PhysicianPatient {
  id: string;
  name: string;
  age: number;
  gaWeeks: number;
  riskFactors: string[];
  activeProblems: string[];
  notesSummary: string;
  timeline: TimelineEvent[];
  suggestions: PhysicianSuggestion[];
}

export const physicianTasks: PhysicianTask[] = [
  {
    id: "T-001",
    patientId: "P-001",
    patientName: "María Fernández",
    patientGA: 28.3,
    kind: "revisar_resumen",
    title: "Revisar resumen extraído",
    subtitle: "Cesárea previa + anemia · pre-consulta",
    status: "pending",
    priority: "high",
    riskLevel: "warn",
  },
  {
    id: "T-002",
    patientId: "P-003",
    patientName: "Andrea Salinas",
    patientGA: 34.5,
    kind: "alerta",
    title: "Glucosa elevada — confirmar",
    subtitle: "Diabetes gestacional · necesita interconsulta",
    status: "pending",
    priority: "high",
    riskLevel: "risk",
  },
  {
    id: "T-003",
    patientId: "P-005",
    patientName: "Rosa Caballero",
    patientGA: 37.2,
    kind: "alerta",
    title: "Preeclampsia leve — control PA",
    subtitle: "Monitoreo semanal hasta el parto",
    status: "in_review",
    priority: "high",
    riskLevel: "risk",
  },
  {
    id: "T-004",
    patientId: "P-008",
    patientName: "Carolina Vargas",
    patientGA: 22.4,
    kind: "agendar",
    title: "Programar eco de control",
    subtitle: "Placenta previa marginal · próxima eco en 2 semanas",
    status: "pending",
    priority: "med",
    riskLevel: "warn",
  },
  {
    id: "T-005",
    patientId: "P-006",
    patientName: "Elena Rojas",
    patientGA: 8.5,
    kind: "validar_lab",
    title: "TSH pendiente de revisión",
    subtitle: "Hipotiroidismo · ajustar dosis si elevada",
    status: "pending",
    priority: "med",
    riskLevel: "warn",
  },
  {
    id: "T-006",
    patientId: "P-002",
    patientName: "Lucía Quispe",
    patientGA: 12.1,
    kind: "revisar_resumen",
    title: "Captación 1er trimestre",
    subtitle: "Sin factores de riesgo · validar suplementos",
    status: "pending",
    priority: "low",
    riskLevel: "ok",
  },
  {
    id: "T-007",
    patientId: "N-007",
    patientName: "Bebé Castro",
    patientGA: 0,
    kind: "handoff",
    title: "Handoff neonatal pendiente",
    subtitle: "Llegando de obstetricia · tamizaje en 24h",
    status: "pending",
    priority: "med",
    riskLevel: "ok",
  },
];

// Detalle del paciente "actual" (P-001, María Fernández) basado en caso 01
export const currentPatient: PhysicianPatient = {
  id: "P-001",
  name: "María Fernández",
  age: 32,
  gaWeeks: 28.3,
  riskFactors: ["Cesárea previa (2022)", "Anemia leve gestacional"],
  activeProblems: ["Anemia leve gestacional", "Cesárea previa (2022)"],
  notesSummary:
    "G2P1 con cesárea previa por desproporción céfalo-pélvica (2022). Gestación actual 28s 2d sin complicaciones agudas. Anemia leve en tratamiento con sulfato ferroso. Plan: cesárea programada a 39 semanas.",
  timeline: timelineEvents.slice(-4),
  suggestions: [
    {
      id: "S-001",
      title: "Confirmar continuidad de sulfato ferroso",
      rationale:
        "Hb 10.8 g/dL en último control. Confirmar adherencia y verificar tolerancia GI.",
      evidence: "Lab 02/04/2026 — Hemoglobina 10.8 g/dL (anormal)",
      confidence: 0.93,
      category: "seguimiento",
    },
    {
      id: "S-002",
      title: "Programar evaluación preanestésica",
      rationale:
        "Cesárea programada a 39s. Evaluación pre-anestésica debe coordinarse 7 días antes (15/06/2026).",
      evidence: "Plan documentado: cesárea programada por cesárea previa",
      confidence: 0.88,
      category: "preparacion",
    },
    {
      id: "S-003",
      title: "Solicitar control hematológico de salida",
      rationale:
        "Repetir Hb a las 35-36 semanas para evaluar respuesta al hierro antes del parto.",
      evidence: "Anemia leve gestacional documentada en 02/04/2026",
      confidence: 0.82,
      category: "documentacion",
    },
    {
      id: "S-004",
      title: "Revisar serologías recientes",
      rationale:
        "HIV, sífilis y otras serologías son del 1er trimestre. Confirmar si se requiere repetición previa al parto según protocolo institucional.",
      evidence: "Última serología documentada: 02/04/2026",
      confidence: 0.71,
      category: "documentacion",
    },
    {
      id: "S-005",
      title: "Counselling sobre signos de alarma",
      rationale:
        "Paciente en T3. Reforzar signos de alarma: cefalea persistente, escotomas, edema, disminución de movimientos fetales.",
      evidence: "EG 28s 2d — inicio de T3",
      confidence: 0.65,
      category: "seguimiento",
    },
  ],
};
