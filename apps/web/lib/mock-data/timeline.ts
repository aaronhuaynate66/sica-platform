/**
 * Eventos sintéticos del journey gestacional para la vista Timeline.
 * Modelado sobre el caso 01 (G2P1, EG 28.3s al "hoy" de la demo).
 *
 * DATOS SINTÉTICOS. No es paciente real.
 */

export type TimelineEventKind =
  | "fum"
  | "control"
  | "ecografia"
  | "laboratorio"
  | "factor_riesgo"
  | "plan";

export type TimelineEventRiskLevel = "ok" | "warn" | "risk";

export interface TimelineEvent {
  id: string;
  week: number; // semana de gestación (puede ser decimal)
  kind: TimelineEventKind;
  title: string;
  description: string;
  riskLevel: TimelineEventRiskLevel;
  date: string; // ISO YYYY-MM-DD
  details: string[]; // bullets para el drawer
}

export const timelineEvents: TimelineEvent[] = [
  {
    id: "fum",
    week: 0,
    kind: "fum",
    title: "FUM",
    description: "Fecha de última menstruación",
    riskLevel: "ok",
    date: "2025-09-15",
    details: [
      "FUM confirmada por la paciente.",
      "FPP estimada: 22/06/2026.",
    ],
  },
  {
    id: "control-8",
    week: 8,
    kind: "control",
    title: "1er control prenatal",
    description: "Captación temprana, examen físico completo",
    riskLevel: "ok",
    date: "2025-11-10",
    details: [
      "Captación dentro del 1er trimestre.",
      "PA 110/70, peso 62 kg.",
      "Suplementación con ácido fólico iniciada.",
    ],
  },
  {
    id: "eco-12",
    week: 12,
    kind: "ecografia",
    title: "Ecografía 1er trimestre",
    description: "Translucencia nucal + datación",
    riskLevel: "ok",
    date: "2025-12-08",
    details: [
      "TN dentro de límites normales.",
      "Edad gestacional ecográfica coherente con FUM.",
      "Riesgo combinado bajo.",
    ],
  },
  {
    id: "lab-trimestre1",
    week: 12,
    kind: "laboratorio",
    title: "Perfil 1er trimestre",
    description: "Hemograma, glicemia, perfil tiroideo, serologías",
    riskLevel: "ok",
    date: "2025-12-10",
    details: [
      "Hb 11.9 g/dL.",
      "TSH 1.8 mUI/L.",
      "Serologías negativas (HIV, sífilis, hepatitis B, toxoplasma IgG +/IgM-).",
    ],
  },
  {
    id: "control-20",
    week: 20,
    kind: "control",
    title: "Control 2do trimestre",
    description: "Movimientos fetales presentes, AU acorde",
    riskLevel: "ok",
    date: "2026-02-02",
    details: [
      "Altura uterina acorde a EG.",
      "Movimientos fetales referidos por la paciente.",
      "PA 115/75.",
    ],
  },
  {
    id: "eco-20",
    week: 20,
    kind: "ecografia",
    title: "Ecografía morfológica",
    description: "Anatomía fetal completa",
    riskLevel: "ok",
    date: "2026-02-05",
    details: [
      "Anatomía fetal sin alteraciones evidentes.",
      "Placenta normoinserta.",
      "Líquido amniótico normal.",
    ],
  },
  {
    id: "factor-cesarea-previa",
    week: 24,
    kind: "factor_riesgo",
    title: "Cesárea previa identificada",
    description: "G2P1 — cesárea segmentaria 2022",
    riskLevel: "warn",
    date: "2026-03-02",
    details: [
      "Cesárea anterior por desproporción céfalo-pélvica (2022).",
      "Plan: cesárea programada a las 39 semanas.",
      "Counselling sobre VBAC realizado y declinado por la paciente.",
    ],
  },
  {
    id: "lab-trimestre3",
    week: 28,
    kind: "laboratorio",
    title: "Perfil 3er trimestre",
    description: "Hb baja: anemia leve",
    riskLevel: "warn",
    date: "2026-04-02",
    details: [
      "Hb 10.8 g/dL — anemia leve gestacional.",
      "TSH 2.1 mUI/L — normal.",
      "Glucosa basal 92 mg/dL — normal.",
      "HIV y sífilis: no reactivos.",
    ],
  },
  {
    id: "control-28",
    week: 28.3,
    kind: "control",
    title: "Control actual",
    description: "EG 28s 2d — sin signos de alarma",
    riskLevel: "warn",
    date: "2026-04-15",
    details: [
      "Indicación: sulfato ferroso 1 tab/día.",
      "Próximo control en 4 semanas o antes si síntomas.",
      "Signos de alarma explicados.",
    ],
  },
  {
    id: "plan-cesarea",
    week: 39,
    kind: "plan",
    title: "Cesárea programada",
    description: "Iterativa por cesárea previa",
    riskLevel: "warn",
    date: "2026-06-15",
    details: [
      "Cesárea programada por cesárea previa.",
      "Coordinar evaluación preanestésica 1 semana antes.",
      "Confirmar laboratorios vigentes.",
    ],
  },
];
