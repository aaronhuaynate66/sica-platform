"use client";

import { useCallback, useMemo, useState } from "react";

import type { ObstetricSummary } from "@/lib/types/obstetric-summary";

export interface FieldEdit {
  path: string;
  original: unknown;
  current: unknown;
}

export interface UseEditableSummary {
  summary: ObstetricSummary;
  editField: (path: string, newValue: unknown) => void;
  resetField: (path: string) => void;
  resetAll: () => void;
  hasEdits: boolean;
  editedFields: string[];
  edits: FieldEdit[];
}

/**
 * Estado editable sobre un ObstetricSummary. R0 mantiene las ediciones
 * en memoria — sin persistencia. R1+ va a sincronizar con el orquestador
 * para alimentar el feedback loop del Data Flywheel (STRATEGY § 9 loop 2).
 *
 * El hook conserva el objeto original (immutable) para poder revertir
 * campo a campo o todo de una vez. Cada edit aplica un setByPath
 * inmutable que reconstruye sólo el camino tocado.
 */
export function useEditableSummary(initial: ObstetricSummary): UseEditableSummary {
  const [original] = useState<ObstetricSummary>(() => structuredClone(initial));
  const [edits, setEdits] = useState<Map<string, FieldEdit>>(() => new Map());

  const summary = useMemo<ObstetricSummary>(() => {
    if (edits.size === 0) return original;
    let next: ObstetricSummary = structuredClone(original);
    for (const edit of edits.values()) {
      next = setByPath(next, edit.path, edit.current) as ObstetricSummary;
    }
    return next;
  }, [edits, original]);

  const editField = useCallback(
    (path: string, newValue: unknown) => {
      const originalValue = getByPath(original, path);
      // Si el valor nuevo es igual al original (estructuralmente), tratamos
      // como "no edit" — equivalente a reset.
      if (deepEqual(originalValue, newValue)) {
        setEdits((prev) => {
          if (!prev.has(path)) return prev;
          const next = new Map(prev);
          next.delete(path);
          return next;
        });
        return;
      }
      setEdits((prev) => {
        const next = new Map(prev);
        next.set(path, {
          path,
          original: originalValue,
          current: newValue,
        });
        return next;
      });
    },
    [original],
  );

  const resetField = useCallback((path: string) => {
    setEdits((prev) => {
      if (!prev.has(path)) return prev;
      const next = new Map(prev);
      next.delete(path);
      return next;
    });
  }, []);

  const resetAll = useCallback(() => {
    setEdits(new Map());
  }, []);

  return {
    summary,
    editField,
    resetField,
    resetAll,
    hasEdits: edits.size > 0,
    editedFields: Array.from(edits.keys()),
    edits: Array.from(edits.values()),
  };
}

// ---------------------------------------------------------------------------
// Helpers — exportados sólo para tests; el consumidor usa el hook.
// ---------------------------------------------------------------------------

export function getByPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc == null || typeof acc !== "object") return undefined;
    return (acc as Record<string, unknown>)[key];
  }, obj);
}

export function setByPath(obj: unknown, path: string, value: unknown): unknown {
  const keys = path.split(".");
  return _set(obj, keys, 0, value);
}

function _set(node: unknown, keys: string[], i: number, value: unknown): unknown {
  if (i >= keys.length) return value;
  const key = keys[i];
  // Detectar índice numérico para preservar arrays como arrays.
  const isIndex = /^\d+$/.test(key);
  if (Array.isArray(node)) {
    const idx = Number(key);
    const copy = node.slice();
    copy[idx] = _set(copy[idx], keys, i + 1, value);
    return copy;
  }
  if (node === null || typeof node !== "object") {
    // Si el path se mete en algo no-objeto, decidimos: crear array si la
    // siguiente key es numérica, sino objeto.
    const fresh: unknown = isIndex ? [] : {};
    return _set(fresh, keys, i, value);
  }
  const obj = node as Record<string, unknown>;
  return {
    ...obj,
    [key]: _set(obj[key], keys, i + 1, value),
  };
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a == null || b == null) return a === b;
  if (typeof a !== typeof b) return false;
  if (typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false;
    }
    return true;
  }
  const keysA = Object.keys(a as object);
  const keysB = Object.keys(b as object);
  if (keysA.length !== keysB.length) return false;
  for (const k of keysA) {
    if (!deepEqual((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k])) {
      return false;
    }
  }
  return true;
}
