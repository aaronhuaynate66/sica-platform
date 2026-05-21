/**
 * Acceso a fixtures sintéticos para la UI demo.
 *
 * Estos son datos 100% sintéticos. Generados por el clinical-extractor
 * sobre un PDF también sintético en services/clinical-extractor/data/.
 *
 * NO ES PACIENTE REAL. Cualquier uso clínico real está fuera de scope
 * mientras la app no tenga validación, auth, ni inscripción de banco de
 * datos personales ante la ANPD (ver STRATEGY § 14).
 */

import type { ObstetricSummary } from "@/lib/types/obstetric-summary";
import syntheticCase01 from "./synthetic_case_01.json";

export const syntheticCase01Summary: ObstetricSummary = syntheticCase01 as ObstetricSummary;

export const syntheticCase01PdfPath = "/synthetic_case_01.pdf";
