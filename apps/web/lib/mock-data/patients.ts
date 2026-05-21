/**
 * Pacientes ficticios para la vista de Dashboard.
 *
 * DEMO DATA · DATOS 100% SINTÉTICOS · NO ES PACIENTE REAL.
 *
 * Nombres, edades y demás campos son inventados. No correlacionan con
 * ninguna persona real ni provienen de ningún sistema clínico productivo.
 */

export type RiskLevel = "ok" | "warn" | "risk";

export interface MockPatient {
  id: string;
  name: string; // ficticio
  age: number;
  gaWeeks: number; // EG semanas
  risk: RiskLevel;
  riskReason: string;
  lastVisit: string; // ISO
  nextVisit: string | null; // ISO o null
  specialty: "obstetricia" | "neonatologia" | "pediatria";
}

export const mockPatients: MockPatient[] = [
  {
    id: "P-001",
    name: "María Fernández",
    age: 32,
    gaWeeks: 28.3,
    risk: "warn",
    riskReason: "Cesárea previa + anemia leve",
    lastVisit: "2026-04-15",
    nextVisit: "2026-05-13",
    specialty: "obstetricia",
  },
  {
    id: "P-002",
    name: "Lucía Quispe",
    age: 24,
    gaWeeks: 12.1,
    risk: "ok",
    riskReason: "Sin factores de riesgo identificados",
    lastVisit: "2026-04-22",
    nextVisit: "2026-05-20",
    specialty: "obstetricia",
  },
  {
    id: "P-003",
    name: "Andrea Salinas",
    age: 38,
    gaWeeks: 34.5,
    risk: "risk",
    riskReason: "Diabetes gestacional + edad materna avanzada",
    lastVisit: "2026-05-10",
    nextVisit: "2026-05-17",
    specialty: "obstetricia",
  },
  {
    id: "P-004",
    name: "Patricia Yáñez",
    age: 29,
    gaWeeks: 19.0,
    risk: "ok",
    riskReason: "Embarazo de bajo riesgo",
    lastVisit: "2026-05-08",
    nextVisit: "2026-06-05",
    specialty: "obstetricia",
  },
  {
    id: "P-005",
    name: "Rosa Caballero",
    age: 41,
    gaWeeks: 37.2,
    risk: "risk",
    riskReason: "Preeclampsia leve, requiere monitoreo semanal",
    lastVisit: "2026-05-12",
    nextVisit: "2026-05-19",
    specialty: "obstetricia",
  },
  {
    id: "P-006",
    name: "Elena Rojas",
    age: 27,
    gaWeeks: 8.5,
    risk: "warn",
    riskReason: "Hipotiroidismo en tratamiento",
    lastVisit: "2026-05-01",
    nextVisit: "2026-05-29",
    specialty: "obstetricia",
  },
  {
    id: "N-007",
    name: "Bebé Castro (madre P-002 ficticio)",
    age: 0,
    gaWeeks: 0,
    risk: "ok",
    riskReason: "Tamizaje neonatal pendiente",
    lastVisit: "2026-05-15",
    nextVisit: "2026-05-21",
    specialty: "neonatologia",
  },
  {
    id: "P-008",
    name: "Carolina Vargas",
    age: 35,
    gaWeeks: 22.4,
    risk: "warn",
    riskReason: "Placenta previa marginal",
    lastVisit: "2026-05-09",
    nextVisit: "2026-05-23",
    specialty: "obstetricia",
  },
  {
    id: "P-009",
    name: "Diana Romero",
    age: 31,
    gaWeeks: 32.0,
    risk: "ok",
    riskReason: "Sin factores de riesgo identificados",
    lastVisit: "2026-05-11",
    nextVisit: "2026-05-25",
    specialty: "obstetricia",
  },
  {
    id: "P-010",
    name: "Sofía Núñez",
    age: 26,
    gaWeeks: 5.3,
    risk: "ok",
    riskReason: "Captación temprana, exámenes pendientes",
    lastVisit: "2026-05-14",
    nextVisit: "2026-06-11",
    specialty: "obstetricia",
  },
];
