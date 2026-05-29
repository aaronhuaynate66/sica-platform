/**
 * Tipos TypeScript que reflejan el esquema Supabase de SICA.
 *
 * Fuente canónica: supabase/migrations/0001_initial_schema.sql
 *
 * Cuando se conecte el MCP/CLI de Supabase, este archivo será reemplazado
 * por `supabase gen types typescript --project-id <id>`. Hasta entonces
 * se mantiene a mano y sincronizado con la migración.
 */

import type { ObstetricSummary } from "@/lib/types/obstetric-summary";

export interface Paciente {
  id: string;
  user_id: string;
  nombre_completo: string;
  dni: string | null;
  hc_id: string | null;
  fecha_nacimiento: string | null;
  created_at: string;
  updated_at: string;
}

export interface PacienteInsert {
  nombre_completo: string;
  dni?: string | null;
  hc_id?: string | null;
  fecha_nacimiento?: string | null;
}

export interface Control {
  id: string;
  paciente_id: string;
  user_id: string;
  pdf_filename: string;
  pdf_storage_path: string | null;
  semanas_gestacion: number | null;
  fecha_control: string | null;
  resumen_json: ObstetricSummary;
  extractor_version: string | null;
  prompt_version: string | null;
  provider_id: string | null;
  confidence_score: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  trace_id: string | null;
  created_at: string;
}

export interface ControlInsert {
  paciente_id: string;
  pdf_filename: string;
  pdf_storage_path?: string | null;
  semanas_gestacion?: number | null;
  fecha_control?: string | null;
  resumen_json: ObstetricSummary;
  extractor_version?: string | null;
  prompt_version?: string | null;
  provider_id?: string | null;
  confidence_score?: number | null;
  cost_usd?: number | null;
  latency_ms?: number | null;
  trace_id?: string | null;
}

export interface PacienteWithStats extends Paciente {
  total_controles: number;
  ultimo_control_fecha: string | null;
  semanas_gestacion_actual: number | null;
}
