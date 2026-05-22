"use client";

import Link from "next/link";
import { Shield, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useConsent } from "@/lib/analytics/use-consent";

const LAST_UPDATED = "22 de mayo de 2026";

export default function PrivacyPage() {
  const { consent, reset } = useConsent();

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <div className="flex items-center gap-2 text-clinical-blue mb-2">
          <Shield className="size-5" />
          <span className="text-xs uppercase tracking-wider font-medium">
            Privacidad y datos
          </span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">
          Privacidad y manejo de datos
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Cómo SICA trata tus datos de uso y los documentos que subes en esta demo
          interna.
        </p>
      </header>

      <section className="space-y-6 text-sm leading-relaxed">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Qué recolectamos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-muted-foreground">
            <p>
              Si das tu consentimiento, recolectamos información agregada sobre cómo
              navegás la plataforma:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-1">
              <li>Tu dirección IP (anonimizada antes de almacenarse).</li>
              <li>Tipo de dispositivo, navegador y resolución de pantalla.</li>
              <li>
                Eventos de uso: qué páginas visitás, qué botones presionás, cuánto
                tarda una extracción.
              </li>
              <li>Region/país aproximado derivado de IP, sin ciudad exacta.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Qué <strong>NO</strong> recolectamos
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-muted-foreground">
            <ul className="list-disc list-inside space-y-1 pl-1">
              <li>
                <strong className="text-foreground">
                  El contenido de PDFs que subes
                </strong>
                : nunca se envía a las herramientas de analítica.
              </li>
              <li>
                <strong className="text-foreground">Datos clínicos extraídos</strong>:
                edad, problemas, laboratorios, plan, etc.{" "}
                <em>Cualquier elemento que muestre datos clínicos lleva un atributo
                  de masking que los oculta en grabaciones de sesión.</em>
              </li>
              <li>
                <strong className="text-foreground">Identificadores de paciente</strong>:
                no procesamos nombres, DNI ni equivalentes.
              </li>
              <li>
                Texto que escribís al editar campos: queda en memoria de tu sesión.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Herramientas usadas</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-muted-foreground">
            <ul className="list-disc list-inside space-y-1 pl-1">
              <li>
                <strong className="text-foreground">Google Analytics 4</strong> (Google
                LLC, EE. UU.) — telemetría de uso agregada. IP anonimizada vía
                {" "}<code className="font-mono text-[11px]">anonymize_ip: true</code>.
              </li>
              <li>
                <strong className="text-foreground">Microsoft Clarity</strong> (Microsoft
                Corp., EE. UU.) — heatmaps + grabaciones de sesión con masking
                automático del contenido sensible.
              </li>
            </ul>
            <p className="text-[11px] mt-2">
              Ambas plataformas son terceros. Sus políticas de privacidad se aplican
              además de la nuestra.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Tus derechos bajo Ley 29733</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-muted-foreground">
            <p>
              Como titular de datos personales en Perú, tenés derecho a:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-1">
              <li>
                <strong className="text-foreground">Acceso</strong>: pedir copia de
                los datos que tengamos sobre vos.
              </li>
              <li>
                <strong className="text-foreground">Rectificación</strong>: corregir
                datos inexactos.
              </li>
              <li>
                <strong className="text-foreground">Cancelación</strong>: pedir que
                borremos tus datos.
              </li>
              <li>
                <strong className="text-foreground">Oposición</strong>: oponerte al
                procesamiento por motivos legítimos.
              </li>
            </ul>
            <p className="text-[11px] mt-2">
              Para ejercer estos derechos, contactá al equipo de SICA por los
              canales del repositorio. Banco de datos personales pendiente de
              inscripción ante la ANPD (ver issue #2 del repo).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Cómo cambiar tu decisión</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-muted-foreground">
            <p>
              Tu decisión actual:{" "}
              <strong
                className={
                  consent === "granted"
                    ? "text-confirm-green"
                    : consent === "denied"
                      ? "text-risk-red"
                      : "text-warn-yellow"
                }
              >
                {consent === "granted"
                  ? "Aceptado"
                  : consent === "denied"
                    ? "Rechazado"
                    : "Pendiente"}
              </strong>
              .
            </p>
            <p>
              Para revisarla, hacé click acá. El banner reaparecerá al volver a la
              página principal.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={reset}
              data-testid="reset-consent"
            >
              <RotateCcw className="size-3" />
              Cambiar mi decisión actual
            </Button>
            <p className="text-[11px]">
              Alternativa técnica: limpiar la entrada{" "}
              <code className="font-mono">sica-analytics-consent</code> de
              localStorage en tu navegador.
            </p>
          </CardContent>
        </Card>
      </section>

      <footer className="mt-10 flex items-center justify-between border-t border-border pt-4 text-[11px] text-muted-foreground">
        <span>Última actualización: {LAST_UPDATED}</span>
        <Link href="/" className="text-clinical-blue hover:underline">
          ← Volver a SICA
        </Link>
      </footer>
    </div>
  );
}
