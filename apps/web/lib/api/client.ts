/**
 * Cliente HTTP tipado para sica-api.
 *
 * Diseño:
 * - Cada call respeta un timeout (default 30s, override por call).
 * - Errores de red, timeout, 4xx y 5xx se diferencian con clases propias
 *   para que la UI pueda decidir qué mensaje mostrar.
 * - NUNCA loggeamos contenido del PDF ni del summary recibido — solo
 *   metadatos en consola para depuración.
 */

import type {
  ApiErrorBody,
  HealthResponse,
  ModelsResponse,
  ObstetricSummary,
} from "./types";
import { ApiError, ApiTimeoutError, ApiUnavailableError } from "./types";

export const DEFAULT_API_URL = "http://localhost:8000";
export const DEFAULT_TIMEOUT_MS = 30_000;
const EXTRACT_TIMEOUT_MS = 60_000; // /extract puede tardar hasta ~30s + buffer

function resolveBaseUrl(override?: string): string {
  if (override) return override.replace(/\/+$/, "");
  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env && env.trim()) return env.trim().replace(/\/+$/, "");
  return DEFAULT_API_URL;
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody | null> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  init: RequestInit,
  timeoutMs: number,
  baseUrlOverride?: string,
): Promise<T> {
  const base = resolveBaseUrl(baseUrlOverride);
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiTimeoutError(`Timeout (${timeoutMs}ms) en ${path}`);
    }
    throw new ApiUnavailableError(
      `No se pudo conectar a sica-api en ${base}${path}: ${
        err instanceof Error ? err.message : String(err)
      }`,
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError({
      status: response.status,
      code: body?.error ?? `http_${response.status}`,
      message: body?.detail ?? `HTTP ${response.status}`,
      requestId: body?.request_id ?? response.headers.get("X-Request-ID"),
      errorId: body?.error_id ?? response.headers.get("X-Error-ID"),
    });
  }

  return (await response.json()) as T;
}

export interface ApiClientOptions {
  baseUrl?: string;
  timeoutMs?: number;
}

export async function getHealth(
  opts: ApiClientOptions = {},
): Promise<HealthResponse> {
  return request<HealthResponse>(
    "/health",
    { method: "GET", headers: { Accept: "application/json" } },
    opts.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    opts.baseUrl,
  );
}

export async function getModels(
  opts: ApiClientOptions = {},
): Promise<ModelsResponse> {
  return request<ModelsResponse>(
    "/models",
    { method: "GET", headers: { Accept: "application/json" } },
    opts.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    opts.baseUrl,
  );
}

export async function extractFromPdf(
  file: File,
  opts: ApiClientOptions = {},
): Promise<ObstetricSummary> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  return request<ObstetricSummary>(
    "/extract",
    {
      method: "POST",
      headers: { Accept: "application/json" },
      body: formData,
    },
    opts.timeoutMs ?? EXTRACT_TIMEOUT_MS,
    opts.baseUrl,
  );
}
