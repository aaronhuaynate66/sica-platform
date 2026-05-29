/**
 * Cliente Supabase para browser components ("use client").
 *
 * Lee NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY del bundle.
 * Si ambos están vacíos (e.g. modo demo sin Supabase configurado), la
 * función levanta a la primera llamada para fallar rápido.
 */

import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "Supabase no está configurado: faltan NEXT_PUBLIC_SUPABASE_URL " +
        "o NEXT_PUBLIC_SUPABASE_ANON_KEY. Ver apps/web/.env.example."
    );
  }

  return createBrowserClient(url, anonKey);
}
