/**
 * Detector del modo activo (live vs demo).
 *
 * Reglas:
 * - NEXT_PUBLIC_API_MODE === "live" → la app intenta usar la API real,
 *   con fallback automático a demo si /health falla.
 * - cualquier otro valor (o no definido) → modo demo, no se llama a la API.
 *
 * El resultado de /health se cachea por 30 segundos para evitar pegarle a
 * la API en cada render. El cache es por instancia de módulo (per-tab).
 */

import { getHealth } from "./client";

export type ApiMode = "live" | "demo";

const CACHE_TTL_MS = 30_000;

interface AvailabilityCache {
  available: boolean;
  checkedAt: number;
}

let cache: AvailabilityCache | null = null;

export function getConfiguredMode(): ApiMode {
  const raw = (process.env.NEXT_PUBLIC_API_MODE ?? "").toLowerCase();
  return raw === "live" ? "live" : "demo";
}

export function clearAvailabilityCache(): void {
  cache = null;
}

/**
 * Hace GET /health y devuelve true si la API responde 200 con un body
 * estructuralmente válido. Cachea el resultado por 30s.
 *
 * En modo demo siempre devuelve false sin pegarle a la red.
 */
export async function isApiAvailable(
  opts: { timeoutMs?: number; forceFresh?: boolean } = {},
): Promise<boolean> {
  if (getConfiguredMode() === "demo") return false;

  const now = Date.now();
  if (!opts.forceFresh && cache && now - cache.checkedAt < CACHE_TTL_MS) {
    return cache.available;
  }

  try {
    const health = await getHealth({ timeoutMs: opts.timeoutMs ?? 3000 });
    const ok = health.status === "ok";
    cache = { available: ok, checkedAt: now };
    return ok;
  } catch {
    cache = { available: false, checkedAt: now };
    return false;
  }
}

/**
 * Resuelve el modo efectivo combinando configuración + disponibilidad real.
 *
 * - configured=demo → "demo"
 * - configured=live + API up → "live"
 * - configured=live + API down → "demo" (fallback degradado)
 */
export async function resolveEffectiveMode(): Promise<ApiMode> {
  const configured = getConfiguredMode();
  if (configured === "demo") return "demo";
  const ok = await isApiAvailable();
  return ok ? "live" : "demo";
}
