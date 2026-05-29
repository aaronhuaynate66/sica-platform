/**
 * Cliente Supabase para Server Components, Route Handlers y Server Actions.
 *
 * Lee/escribe cookies vía next/headers. El try/catch sobre `setAll` cubre
 * el caso de Server Components puros donde set no está permitido —
 * Supabase mismo recomienda este pattern.
 */

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "Supabase no está configurado: faltan NEXT_PUBLIC_SUPABASE_URL " +
        "o NEXT_PUBLIC_SUPABASE_ANON_KEY. Ver apps/web/.env.example."
    );
  }

  return createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options);
          });
        } catch {
          // Llamado desde un Server Component donde mutar cookies no está
          // permitido. El middleware refresca la sesión, así que ignorar
          // este caso es seguro.
        }
      },
    },
  });
}
