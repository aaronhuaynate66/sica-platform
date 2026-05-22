/**
 * Catálogo de eventos de analytics de SICA web.
 *
 * Cada vez que se agregue un evento nuevo:
 *  1. Agregar la constante acá.
 *  2. Documentar qué dispara el evento + qué params lleva.
 *  3. Validar que los params son seguros (no PHI). Ver
 *     `lib/analytics/use-analytics.ts` sanitizeParams.
 *
 * Convención de nombres: snake_case, verbo en pasado para acciones
 * completadas. Ej. "edit_saved", no "save_edit".
 */
export const ANALYTICS_EVENTS = {
  // ---- Navegación ----------------------------------------------------------
  /** SPA nav entre vistas. Params: { from: string, to: string } */
  VIEW_CHANGED: "view_changed",

  // ---- Upload flow ---------------------------------------------------------
  /** Click "Cargar PDF de ejemplo". Sin params. */
  EXAMPLE_PDF_LOADED: "example_pdf_loaded",
  /** Click "Subir PDF propio". Sin params (la selección de archivo viene luego). */
  CUSTOM_PDF_UPLOAD_STARTED: "custom_pdf_upload_started",
  /** Extracción del PDF subido completó OK. Params: { duration_ms, mode } */
  CUSTOM_PDF_UPLOAD_SUCCESS: "custom_pdf_upload_success",
  /** Extracción falló. Params: { error_type } — NUNCA mensaje completo. */
  CUSTOM_PDF_UPLOAD_ERROR: "custom_pdf_upload_error",

  // ---- Evidencia trazable --------------------------------------------------
  /** Abre el modal de evidencia para un campo. Params: { field_name } */
  EVIDENCE_OPENED: "evidence_opened",
  /** Click "Abrir PDF en página N" desde un evidence span. Params: { page_number } */
  EVIDENCE_PDF_LINK_CLICKED: "evidence_pdf_link_clicked",

  // ---- Edición inline ------------------------------------------------------
  /** Click ✏️ en un campo editable. Params: { field_path } */
  EDIT_STARTED: "edit_started",
  /** Guarda una edición. Params: { field_path } — NUNCA el valor nuevo. */
  EDIT_SAVED: "edit_saved",
  /** Cancela una edición en curso. Sin params. */
  EDIT_CANCELED: "edit_canceled",
  /** Revierte un campo editado al original. Params: { field_path } */
  EDIT_REVERTED: "edit_reverted",
  /** "Descartar todo" en el modal de cambios. Params: { edits_count } */
  EDITS_DISCARDED_ALL: "edits_discarded_all",
  /** Abre el modal "Ver cambios". Sin params. */
  EDITS_DIFF_OPENED: "edits_diff_opened",

  // ---- Consent -------------------------------------------------------------
  /** Usuario acepta analytics. Sin params. */
  CONSENT_GRANTED: "consent_granted",
  /** Usuario rechaza analytics. NO se envía (no hay analytics activos). */
  CONSENT_DENIED: "consent_denied",
  /** Usuario resetea su decisión desde /privacy. */
  CONSENT_RESET: "consent_reset",
} as const;

export type AnalyticsEventName =
  (typeof ANALYTICS_EVENTS)[keyof typeof ANALYTICS_EVENTS];
