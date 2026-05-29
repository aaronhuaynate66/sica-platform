/**
 * Middleware de sesión Supabase + protección de rutas /app/*.
 *
 * El @supabase/ssr middleware refresca la cookie de sesión en cada
 * request. Si no hay user autenticado y la ruta es /app/*, redirige a
 * /login.
 *
 * Si Supabase no está configurado (env vars vacías), el middleware no
 * intenta validar sesión y deja pasar el request — esto preserva la
 * demo pública (/, /timeline, /dashboard, /physician) que funciona sin
 * auth.
 */

import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Sin Supabase configurado: rutas demo pasan; /app/* devuelve 404 vía
  // notFound implícito porque la página requiere un cliente válido.
  if (!url || !anonKey) {
    return NextResponse.next({ request });
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => {
          request.cookies.set(name, value);
        });
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  // IMPORTANTE: getUser() valida el JWT contra Supabase auth; getSession()
  // confía en la cookie y no es seguro server-side.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const pathname = request.nextUrl.pathname;

  // Protege /app/*
  if (!user && pathname.startsWith("/app")) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    redirectUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(redirectUrl);
  }

  // Si ya está autenticado y va a /login, mandarlo a /app.
  if (user && pathname === "/login") {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/app";
    redirectUrl.search = "";
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}

export const config = {
  matcher: [
    // Excluye assets estáticos, imágenes optimizadas, favicon, archivos públicos.
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|pdf)$).*)",
  ],
};
