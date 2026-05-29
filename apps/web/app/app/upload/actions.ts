"use server";

/**
 * Server action: subir PDF → llamar a sica-api → persistir control.
 *
 * Esta es la ruta crítica del frontend. Cualquier falla aquí queda
 * visible al médico, así que cada paso comunica un error legible.
 *
 * Costo del happy path (R1, provider anthropic):
 *   - 1 upload Storage (~MB)
 *   - 1 POST /extract (~USD 0.04, 20-50s con cold start de Render)
 *   - 1 INSERT controles
 *
 * El PDF original queda en Storage como respaldo. Si el /extract falla,
 * NO insertamos en controles y el PDF se queda como huérfano — eso es
 * deliberado: si vuelven a intentar el upload, queda otra copia, pero
 * eso es preferible a perder evidencia del intento.
 */

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createControl } from "@/lib/queries/controles";
import { createPaciente, getPaciente } from "@/lib/queries/pacientes";
import { createClient } from "@/lib/supabase/server";
import type { ExtractResponse, ExtractionMetadata } from "@/lib/api/types";
import type { ObstetricSummary } from "@/lib/types/obstetric-summary";

const EXTRACT_TIMEOUT_MS = 90_000; // 90s: cubre cold start de Render + extraccion ~30s
const PDF_MAGIC = "%PDF-";

export interface ProcessPdfResult {
  ok: boolean;
  error?: string;
  controlId?: string;
  pacienteId?: string;
}

function getApiUrl(): string {
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (!env || !env.trim()) {
    throw new Error("NEXT_PUBLIC_API_URL no está configurado");
  }
  return env.trim().replace(/\/+$/, "");
}

/**
 * Elimina el campo `metadata` del response para persistir solo el
 * `ObstetricSummary` canónico en `resumen_json`. `metadata` viaja por
 * separado en columnas dedicadas de la tabla `controles`.
 */
function stripMetadata(payload: ExtractResponse): ObstetricSummary {
  // Destructuramos para descartar `metadata` sin mutar el objeto original.
  const { metadata: _metadata, ...summary } = payload;
  void _metadata;
  return summary;
}

export async function processPdfAction(
  formData: FormData
): Promise<ProcessPdfResult> {
  const supabase = await createClient();

  // ---- 1. Auth
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return { ok: false, error: "No autenticado" };
  }

  // ---- 2. Validar input
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, error: "Debes seleccionar un PDF válido" };
  }

  // Validación liviana de magic bytes — el API hace la validación autoritativa.
  const headBuf = await file.slice(0, PDF_MAGIC.length).arrayBuffer();
  const headStr = new TextDecoder("latin1").decode(new Uint8Array(headBuf));
  if (headStr !== PDF_MAGIC) {
    return { ok: false, error: "El archivo no es un PDF válido" };
  }

  const mode = (formData.get("mode") as string | null) ?? "existing";
  let pacienteId = (formData.get("paciente_id") as string | null) ?? null;

  // ---- 3. Crear paciente nuevo o validar existente
  if (mode === "new") {
    const nombreCompleto = String(formData.get("nombre_completo") ?? "").trim();
    if (!nombreCompleto) {
      return { ok: false, error: "El nombre completo del paciente es requerido" };
    }
    const dni = String(formData.get("dni") ?? "").trim() || null;
    const fechaNacimiento =
      String(formData.get("fecha_nacimiento") ?? "").trim() || null;

    try {
      const paciente = await createPaciente(supabase, {
        nombre_completo: nombreCompleto,
        dni,
        fecha_nacimiento: fechaNacimiento,
      });
      pacienteId = paciente.id;
    } catch (err) {
      return {
        ok: false,
        error: err instanceof Error ? err.message : "Error creando paciente",
      };
    }
  } else {
    if (!pacienteId) {
      return { ok: false, error: "Selecciona un paciente o crea uno nuevo" };
    }
    const existing = await getPaciente(supabase, pacienteId);
    if (!existing) {
      return { ok: false, error: "El paciente seleccionado no existe" };
    }
  }

  // ---- 4. Subir PDF a Storage. Path: {user_id}/{paciente_id}/{ts}-{filename}
  // Sanitizo filename para no romper el path. Mantengo .pdf al final.
  const safeFilename = file.name
    .replace(/[^a-zA-Z0-9._-]/g, "_")
    .replace(/_+/g, "_");
  const storagePath = `${user.id}/${pacienteId}/${Date.now()}-${safeFilename}`;

  const { error: uploadError } = await supabase.storage
    .from("pdfs")
    .upload(storagePath, file, {
      contentType: "application/pdf",
      upsert: false,
    });

  if (uploadError) {
    return {
      ok: false,
      error: `No se pudo subir el PDF: ${uploadError.message}`,
    };
  }

  // ---- 5. Llamar /extract con el PDF. Reconstruimos FormData para
  // multipart porque el File ya fue leído por upload — pero los Files
  // de FormData son streams reusables en Node 24+ a través de fetch.
  const apiUrl = getApiUrl();
  const extractForm = new FormData();
  extractForm.append("file", file, file.name);

  const started = Date.now();
  let extractBody: ExtractResponse;
  let extractionMetadata: ExtractionMetadata | null = null;
  let traceIdFromHeader: string | null = null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), EXTRACT_TIMEOUT_MS);

  try {
    const res = await fetch(`${apiUrl}/extract`, {
      method: "POST",
      body: extractForm,
      signal: controller.signal,
    });

    traceIdFromHeader = res.headers.get("X-Request-ID");

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = (await res.json()) as { detail?: string; error?: string };
        if (body?.detail) detail = body.detail;
        else if (body?.error) detail = body.error;
      } catch {
        // body no era JSON parseable
      }
      return {
        ok: false,
        error: `Error procesando el PDF: ${detail}`,
      };
    }

    // El response tiene los campos del summary al top-level + un campo
    // "metadata" agregado en commit 2555269. Para clientes antiguos que
    // no leen metadata, el shape sigue siendo el ObstetricSummary; aquí
    // sí lo leemos para persistir trazabilidad.
    extractBody = (await res.json()) as ExtractResponse;
    extractionMetadata = extractBody.metadata ?? null;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return {
        ok: false,
        error: "El procesamiento tardó demasiado (>90s). Inténtalo de nuevo.",
      };
    }
    return {
      ok: false,
      error: `No se pudo conectar a sica-api: ${
        err instanceof Error ? err.message : String(err)
      }`,
    };
  } finally {
    clearTimeout(timer);
  }

  const latencyMs = Date.now() - started;
  // Preferir la latencia que mide el extractor (sin red cliente→Render);
  // si no viene, caer al timer client-side.
  const persistedLatencyMs = extractionMetadata?.latency_ms ?? latencyMs;
  // trace_id viene del bloque metadata cuando Langfuse está activo en
  // el backend; si no, eco del X-Request-ID del header.
  const persistedTraceId =
    extractionMetadata?.trace_id ?? traceIdFromHeader;

  // El summary persistido NO debe llevar el campo "metadata" embebido
  // (no es parte del schema canónico ObstetricSummary).
  const summaryForJsonb: ObstetricSummary = stripMetadata(extractBody);

  // ---- 6. Insert control
  try {
    const control = await createControl(supabase, {
      paciente_id: pacienteId!,
      pdf_filename: file.name,
      pdf_storage_path: storagePath,
      semanas_gestacion: summaryForJsonb.gestational_age_weeks ?? null,
      // R1: el extractor no devuelve fecha del control directamente.
      // Usamos la fecha de hoy como aproximación operacional.
      fecha_control: new Date().toISOString().slice(0, 10),
      resumen_json: summaryForJsonb,
      confidence_score: summaryForJsonb.confidence_score ?? null,
      extractor_version: extractionMetadata?.model_used ?? null,
      prompt_version: extractionMetadata?.prompt_version ?? null,
      provider_id: extractionMetadata?.provider_id ?? null,
      cost_usd: extractionMetadata?.cost_usd ?? null,
      latency_ms: persistedLatencyMs,
      trace_id: persistedTraceId,
    });

    revalidatePath("/app");
    revalidatePath(`/app/pacientes/${pacienteId}`);

    // Devolvemos el id en lugar de redirect adentro porque el redirect
    // de Next requiere throw dentro de un Server Component / action;
    // el caller (page.tsx) decide cómo seguir.
    return {
      ok: true,
      controlId: control.id,
      pacienteId: pacienteId!,
    };
  } catch (err) {
    return {
      ok: false,
      error: `Resumen extraído pero falló al guardar: ${
        err instanceof Error ? err.message : String(err)
      }`,
    };
  }
}

export async function redirectToControl(
  pacienteId: string,
  controlId: string
): Promise<never> {
  redirect(`/app/pacientes/${pacienteId}/controles/${controlId}`);
}
