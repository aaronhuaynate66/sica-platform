/**
 * Helpers de queries Supabase para `pacientes`.
 *
 * Todas las funciones reciben el cliente Supabase como parámetro para
 * que el caller controle si es browser o SSR. RLS hace el aislamiento
 * por user_id — no agregamos filtros redundantes salvo defensa.
 */

import type { SupabaseClient } from "@supabase/supabase-js";

import type {
  Paciente,
  PacienteInsert,
  PacienteWithStats,
} from "@/lib/types/database";

export async function listPacientesWithStats(
  supabase: SupabaseClient
): Promise<PacienteWithStats[]> {
  const { data: pacientes, error } = await supabase
    .from("pacientes")
    .select("*")
    .order("updated_at", { ascending: false });

  if (error) {
    throw new Error(`Error cargando pacientes: ${error.message}`);
  }

  if (!pacientes || pacientes.length === 0) return [];

  // Trae todos los controles del médico de una sola pasada, indexa en memoria.
  // Volumen R1 ≤ centenas de controles → o(n) en memoria es trivial.
  const { data: controles, error: errControles } = await supabase
    .from("controles")
    .select("paciente_id, fecha_control, semanas_gestacion, created_at")
    .order("fecha_control", { ascending: false, nullsFirst: false });

  if (errControles) {
    throw new Error(`Error cargando controles: ${errControles.message}`);
  }

  const statsByPaciente = new Map<
    string,
    { total: number; ultimaFecha: string | null; semanas: number | null }
  >();

  for (const c of controles ?? []) {
    const current = statsByPaciente.get(c.paciente_id) ?? {
      total: 0,
      ultimaFecha: null,
      semanas: null,
    };
    current.total += 1;
    // El orden es desc por fecha_control con nullsFirst:false → el primero por
    // paciente_id es el más reciente con fecha. Si todas son null, queda null.
    if (current.ultimaFecha === null && c.fecha_control) {
      current.ultimaFecha = c.fecha_control;
      current.semanas = c.semanas_gestacion;
    }
    statsByPaciente.set(c.paciente_id, current);
  }

  return (pacientes as Paciente[]).map((p) => {
    const stats = statsByPaciente.get(p.id);
    return {
      ...p,
      total_controles: stats?.total ?? 0,
      ultimo_control_fecha: stats?.ultimaFecha ?? null,
      semanas_gestacion_actual: stats?.semanas ?? null,
    };
  });
}

export async function getPaciente(
  supabase: SupabaseClient,
  id: string
): Promise<Paciente | null> {
  const { data, error } = await supabase
    .from("pacientes")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) {
    throw new Error(`Error cargando paciente: ${error.message}`);
  }
  return data as Paciente | null;
}

export async function createPaciente(
  supabase: SupabaseClient,
  input: PacienteInsert
): Promise<Paciente> {
  const { data: user } = await supabase.auth.getUser();
  if (!user.user) throw new Error("No autenticado");

  const { data, error } = await supabase
    .from("pacientes")
    .insert({
      user_id: user.user.id,
      nombre_completo: input.nombre_completo,
      dni: input.dni ?? null,
      hc_id: input.hc_id ?? null,
      fecha_nacimiento: input.fecha_nacimiento ?? null,
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Error creando paciente: ${error.message}`);
  }
  return data as Paciente;
}

export async function findPacienteByDni(
  supabase: SupabaseClient,
  dni: string
): Promise<Paciente | null> {
  const { data, error } = await supabase
    .from("pacientes")
    .select("*")
    .eq("dni", dni)
    .maybeSingle();

  if (error) {
    throw new Error(`Error buscando paciente por DNI: ${error.message}`);
  }
  return data as Paciente | null;
}
