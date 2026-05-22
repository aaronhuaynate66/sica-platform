"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Estado del consentimiento del usuario para analítica (GA4 + Clarity).
 *
 * - "pending"  → todavía no decidió. Default al primer load. El banner se muestra.
 * - "granted"  → aceptó. Los scripts de analytics pueden cargarse.
 * - "denied"   → rechazó. Ningún script de analytics se carga.
 *
 * Persiste en localStorage bajo `STORAGE_KEY`. Re-abrir la pestaña preserva
 * la decisión. Limpiar localStorage del browser vuelve a "pending".
 *
 * Coherente con Ley 29733 (Perú): el procesamiento de datos personales
 * (IP, fingerprints, telemetría) requiere consentimiento previo, expreso,
 * inequívoco e informado. Hasta que `consent === "granted"`, ningún
 * tracker debe ejecutarse.
 */

export type ConsentState = "granted" | "denied" | "pending";

export const STORAGE_KEY = "sica-analytics-consent";

function readStored(): ConsentState {
  if (typeof window === "undefined") return "pending";
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "granted" || raw === "denied" || raw === "pending") return raw;
    return "pending";
  } catch {
    // localStorage puede estar bloqueado (modo privado, cookies disabled).
    // Default seguro: tracking off.
    return "pending";
  }
}

function writeStored(state: ConsentState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, state);
    // Notificar a otras pestañas + a otros consumidores del hook en
    // la misma pestaña vía StorageEvent custom.
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: STORAGE_KEY,
        newValue: state,
      }),
    );
  } catch {
    /* silent — modo privado o quota exceeded */
  }
}

export interface UseConsent {
  consent: ConsentState;
  accept: () => void;
  decline: () => void;
  reset: () => void;
}

export function useConsent(): UseConsent {
  // SSR-safe: empieza en "pending" en server. En cliente sincroniza con
  // localStorage en el primer efecto.
  const [consent, setConsent] = useState<ConsentState>("pending");

  useEffect(() => {
    setConsent(readStored());

    function onStorage(e: StorageEvent) {
      if (e.key !== STORAGE_KEY) return;
      const next = e.newValue;
      if (next === "granted" || next === "denied" || next === "pending") {
        setConsent(next);
      } else if (next === null) {
        setConsent("pending");
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const accept = useCallback(() => {
    setConsent("granted");
    writeStored("granted");
  }, []);

  const decline = useCallback(() => {
    setConsent("denied");
    writeStored("denied");
  }, []);

  const reset = useCallback(() => {
    setConsent("pending");
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(STORAGE_KEY);
        window.dispatchEvent(
          new StorageEvent("storage", { key: STORAGE_KEY, newValue: null }),
        );
      } catch {
        /* silent */
      }
    }
  }, []);

  return { consent, accept, decline, reset };
}
