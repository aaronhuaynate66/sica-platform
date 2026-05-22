"use client";

import { useCallback } from "react";

import { useConsent } from "./use-consent";

/**
 * Hook para emitir eventos a GA4 y Clarity desde componentes.
 *
 * Garantías:
 *  - Si consent !== "granted" → noop silencioso. Ninguna llamada a gtag/clarity.
 *  - Si window.gtag existe → gtag("event", eventName, sanitizedParams).
 *  - Si window.clarity existe → clarity("event", eventName) (Clarity no
 *    soporta params en eventos custom).
 *  - sanitizeParams() rechaza valores sospechosos de ser PHI:
 *      * strings >MAX_PARAM_STRING_LENGTH chars → omitidos (warn en dev)
 *      * objetos / arrays anidados → omitidos
 *      * undefined / null → omitidos
 *      * números, booleans, strings cortos → permitidos
 *  - El warning de PHI sospechoso sólo se loggea en development; en prod
 *    se omite silenciosamente para no leakear info al usuario.
 */

const MAX_PARAM_STRING_LENGTH = 100;

export type EventParams = Record<
  string,
  string | number | boolean | null | undefined
>;

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    clarity?: (...args: unknown[]) => void;
  }
}

export interface UseAnalytics {
  trackEvent: (eventName: string, params?: EventParams) => void;
  trackPageView: (path: string) => void;
  isReady: boolean;
}

/**
 * Sanitiza un objeto de params eliminando valores que podrían contener PHI.
 * Exportado para testeo unitario.
 */
export function sanitizeParams(
  params: EventParams | undefined,
): Record<string, string | number | boolean> {
  if (!params) return {};
  const safe: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue;
    if (typeof value === "number" || typeof value === "boolean") {
      safe[key] = value;
      continue;
    }
    if (typeof value === "string") {
      if (value.length === 0) continue;
      if (value.length > MAX_PARAM_STRING_LENGTH) {
        if (process.env.NODE_ENV !== "production") {
          console.warn(
            `[sica-analytics] dropped param "${key}": string length ${value.length} > ${MAX_PARAM_STRING_LENGTH} (likely PHI)`,
          );
        }
        continue;
      }
      safe[key] = value;
      continue;
    }
    // objects, arrays, functions, etc → drop
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        `[sica-analytics] dropped param "${key}": type ${typeof value} not allowed`,
      );
    }
  }
  return safe;
}

export function useAnalytics(): UseAnalytics {
  const { consent } = useConsent();

  const trackEvent = useCallback(
    (eventName: string, params?: EventParams) => {
      if (consent !== "granted") return;
      if (typeof window === "undefined") return;
      const safe = sanitizeParams(params);
      try {
        if (typeof window.gtag === "function") {
          window.gtag("event", eventName, safe);
        }
        if (typeof window.clarity === "function") {
          // Clarity event con tag: pasamos el eventName como tag para que
          // aparezca en el dashboard. Los params no se mandan a Clarity.
          window.clarity("event", eventName);
        }
      } catch {
        /* analytics falla silently */
      }
    },
    [consent],
  );

  const trackPageView = useCallback(
    (path: string) => {
      if (consent !== "granted") return;
      if (typeof window === "undefined") return;
      try {
        if (typeof window.gtag === "function") {
          window.gtag("event", "page_view", { page_path: path });
        }
        if (typeof window.clarity === "function") {
          window.clarity("set", "page", path);
        }
      } catch {
        /* silent */
      }
    },
    [consent],
  );

  const isReady =
    consent === "granted" &&
    typeof window !== "undefined" &&
    (typeof window.gtag === "function" || typeof window.clarity === "function");

  return { trackEvent, trackPageView, isReady };
}
