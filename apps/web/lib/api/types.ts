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

export interface HealthResponse {
  status: string;
  version: string;
  extractor_available: boolean;
}

export interface ModelInfo {
  id: string;
  provider: string;
  type: "cloud" | "local" | string;
  phi_allowed: boolean;
  active: boolean;
  role: "default" | "fallback" | "dev_only" | "prohibited" | string;
  notes: string;
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
