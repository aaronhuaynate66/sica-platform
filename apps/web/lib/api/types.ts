/**
 * Tipos del cliente HTTP de sica-api.
 *
 * Espejan los schemas Pydantic en `apps/api/src/sica_api/schemas.py`.
 * Cuando esos cambien, este archivo debe sincronizarse manualmente.
 *
 * Re-exporta los tipos de extracción desde `@/lib/types/obstetric-summary`
 * que ya viven en la web — no duplicamos.
 */

export type {
  EvidenceSpan,
  LabResult,
  ObstetricSummary,
} from "@/lib/types/obstetric-summary";

/**
 * Metadata operacional adjunta al response 200 de POST /extract.
 *
 * Espeja el modelo Pydantic ``ExtractionMetadata`` en
 * apps/api/src/sica_api/schemas.py. Es **aditivo**: los campos del
 * ObstetricSummary siguen al top-level del response — esta interface
 * vive bajo la clave ``metadata`` del mismo objeto.
 */
export interface ExtractionMetadata {
  operation_id: string;
  provider_id: string | null;
  model_used: string;
  prompt_version: string;
  prompt_hash: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number;
  retry_count: number;
  success: boolean;
  error_type: string | null;
  trace_id: string | null;
  request_id: string;
}

/**
 * Response del endpoint POST /extract.
 *
 * El backend devuelve un objeto que combina los campos del
 * ``ObstetricSummary`` al top-level + un campo ``metadata`` con la
 * trazabilidad operacional. Esta forma intersección refleja exactamente
 * ese shape.
 */
import type { ObstetricSummary as _ObstetricSummary } from "@/lib/types/obstetric-summary";
export type ExtractResponse = _ObstetricSummary & {
  metadata: ExtractionMetadata;
};

export interface HealthResponse {
  status: string;
  version: string;
  extractor_available: boolean;
  /** UTC ISO 8601 timestamp del momento de la respuesta. */
  timestamp: string;
}

export interface ModelInfo {
  id: string;
  provider: string;
  type: "cloud" | "local" | string;
  phi_allowed: boolean;
  active: boolean;
  role: "default" | "fallback" | "dev_only" | "prohibited" | string;
  notes: string;
  /**
   * Runtime: true si hay un LLMProvider registrado en el backend, soporta
   * este modelo y reporta credenciales presentes. Distinto de `active`
   * (que es decisión de política).
   */
  is_available?: boolean;
  /** ID del LLMProvider que atiende este modelo, o null si no hay provider implementado aún. */
  provider_id?: string | null;
}

export type ModelsResponse = ModelInfo[];

export interface ApiErrorBody {
  error: string;
  detail: string;
  request_id: string;
  error_id?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly errorId: string | null;

  constructor(opts: {
    status: number;
    code: string;
    message: string;
    requestId?: string | null;
    errorId?: string | null;
  }) {
    super(opts.message);
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.requestId = opts.requestId ?? null;
    this.errorId = opts.errorId ?? null;
  }
}

export class ApiTimeoutError extends Error {
  constructor(message = "Timeout reached calling sica-api") {
    super(message);
    this.name = "ApiTimeoutError";
  }
}

export class ApiUnavailableError extends Error {
  constructor(message = "sica-api is not reachable") {
    super(message);
    this.name = "ApiUnavailableError";
  }
}
