/**
 * Helpers de queries Supabase para `controles`.
 */

import type { SupabaseClient } from "@supabase/supabase-js";

import type { Control, ControlInsert } from "@/lib/types/database";

export async function listControlesByPaciente(
  supabase: SupabaseClient,
  pacienteId: string
): Promise<Control[]> {
  const { data, error } = await supabase
    .from("controles")
    .select("*")
    .eq("paciente_id", pacienteId)
    .order("fecha_control", { ascending: true, nullsFirst: true })
    .order("created_at", { ascending: true });

  if (error) {
    throw new Error(`Error cargando controles: ${error.message}`);
  }
  return (data ?? []) as Control[];
}

export async function getControl(
  supabase: SupabaseClient,
  id: string
): Promise<Control | null> {
  const { data, error } = await supabase
    .from("controles")
    .select("*")
    .eq("id", id)
    .maybeSingle();

  if (error) {
    throw new Error(`Error cargando control: ${error.message}`);
  }
  return data as Control | null;
}

export async function createControl(
  supabase: SupabaseClient,
  input: ControlInsert
): Promise<Control> {
  const { data: user } = await supabase.auth.getUser();
  if (!user.user) throw new Error("No autenticado");

  const { data, error } = await supabase
    .from("controles")
    .insert({
      ...input,
      user_id: user.user.id,
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Error creando control: ${error.message}`);
  }
  return data as Control;
}
