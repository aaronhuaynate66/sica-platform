/**
 * Helpers de fecha en español (es-PE).
 *
 * Todos aceptan `string | null | undefined` y devuelven `"—"` si no hay
 * valor. El formato es corto y predecible — sin años cuando son del año
 * en curso para densidad informacional.
 */

const DATE_FORMATTER = new Intl.DateTimeFormat("es-PE", {
  year: "numeric",
  month: "short",
  day: "2-digit",
});

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat("es-PE", {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateEs(input: string | null | undefined): string {
  if (!input) return "—";
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return "—";
  return DATE_FORMATTER.format(d);
}

export function formatDateTimeEs(input: string | null | undefined): string {
  if (!input) return "—";
  const d = new Date(input);
  if (Number.isNaN(d.getTime())) return "—";
  return DATE_TIME_FORMATTER.format(d);
}

/** Edad en años cumplidos hasta hoy, o null si la fecha es inválida. */
export function calculateAge(birthDate: string | null | undefined): number | null {
  if (!birthDate) return null;
  const dob = new Date(birthDate);
  if (Number.isNaN(dob.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const m = now.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < dob.getDate())) age -= 1;
  return age;
}
