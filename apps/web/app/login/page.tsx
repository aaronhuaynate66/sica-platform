"use client";

/**
 * Login con magic link (Supabase Auth OTP por email).
 *
 * Flujo:
 * 1. Usuario ingresa email.
 * 2. signInWithOtp envía link.
 * 3. Cuando hace click, llega a /auth/callback?code=...
 * 4. callback intercambia code → session y redirige a /app (o ?next=).
 */

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Activity, Loader2, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

type Status =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent"; email: string }
  | { kind: "error"; message: string };

function LoginForm() {
  const params = useSearchParams();
  const nextPath = params.get("next") ?? "/app";
  const callbackError = params.get("error");

  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>(
    callbackError
      ? { kind: "error", message: decodeURIComponent(callbackError) }
      : { kind: "idle" }
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || status.kind === "sending") return;

    setStatus({ kind: "sending" });

    try {
      const supabase = createClient();
      const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`;

      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: redirectTo },
      });

      if (error) {
        setStatus({ kind: "error", message: error.message });
        return;
      }

      setStatus({ kind: "sent", email });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "Error desconocido",
      });
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-clinical-blue/10">
            <Activity className="size-6 text-clinical-blue" />
          </div>
          <CardTitle className="text-2xl">SICA</CardTitle>
          <CardDescription>
            Acceso solo para médicos colaboradores. Te enviamos un enlace al email.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status.kind === "sent" ? (
            <div className="space-y-4 text-center">
              <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-emerald-500/10">
                <Mail className="size-6 text-emerald-500" />
              </div>
              <div className="space-y-1">
                <p className="font-medium">Revisa tu email</p>
                <p className="text-sm text-muted-foreground">
                  Enviamos un enlace de acceso a <strong>{status.email}</strong>.
                  Puede tardar 1-2 minutos en llegar.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStatus({ kind: "idle" })}
                className="mt-4"
              >
                Usar otro email
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="medico@clinica.pe"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={status.kind === "sending"}
                />
              </div>
              {status.kind === "error" && (
                <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {status.message}
                </p>
              )}
              <Button
                type="submit"
                className="w-full"
                disabled={status.kind === "sending" || !email}
              >
                {status.kind === "sending" ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Enviando enlace…
                  </>
                ) : (
                  <>
                    <Mail className="mr-2 size-4" />
                    Enviar enlace de acceso
                  </>
                )}
              </Button>
              <p className="text-center text-xs text-muted-foreground">
                Al continuar aceptas el uso de SICA bajo las condiciones de la{" "}
                <Link href="/privacy" className="underline underline-offset-2">
                  política de privacidad
                </Link>
                .
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
