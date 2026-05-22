"use client";

import { Cookie, X } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ANALYTICS_EVENTS } from "@/lib/analytics/events";
import { useConsent } from "@/lib/analytics/use-consent";

/**
 * Banner sticky de consentimiento para herramientas de analítica.
 * Sólo se renderiza cuando `consent === "pending"`. Texto + decisión
 * coherente con Ley 29733 (consentimiento previo, expreso, informado).
 *
 * Para callbacks adicionales (p. ej. trackear la decisión), aceptar
 * `onAccept` / `onDecline` como props opcionales que se llaman ANTES de
 * grabar el estado.
 */
interface ConsentBannerProps {
  onAccept?: () => void;
  onDecline?: () => void;
}

export function ConsentBanner({ onAccept, onDecline }: ConsentBannerProps = {}) {
  const { consent, accept, decline } = useConsent();

  if (consent !== "pending") return null;

  function handleAccept() {
    onAccept?.();
    accept();
    // Disparo directo (bypass useAnalytics): justo recién consintió, el
    // hook todavía tiene el closure de "pending" en este tick. Damos 150ms
    // para que el script de gtag termine de cargar (next/script
    // afterInteractive). Si no carga a tiempo, el evento se pierde —
    // aceptable para este evento de baja prioridad.
    setTimeout(() => {
      if (typeof window === "undefined") return;
      try {
        if (typeof window.gtag === "function") {
          window.gtag("event", ANALYTICS_EVENTS.CONSENT_GRANTED);
        }
        if (typeof window.clarity === "function") {
          window.clarity("event", ANALYTICS_EVENTS.CONSENT_GRANTED);
        }
      } catch {
        /* silent */
      }
    }, 150);
  }
  function handleDecline() {
    onDecline?.();
    decline();
    // CONSENT_DENIED no se manda — no hay analytics activos.
  }

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Aviso de consentimiento de analítica"
      className="fixed inset-x-0 bottom-9 z-40 border-t border-border bg-background/98 backdrop-blur supports-[backdrop-filter]:bg-background/95 shadow-lg"
      data-testid="consent-banner"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2.5">
          <Cookie className="size-4 text-clinical-blue shrink-0 mt-0.5" />
          <p className="text-xs leading-relaxed text-muted-foreground max-w-3xl">
            SICA usa herramientas de análisis (Google Analytics y Microsoft Clarity)
            para entender cómo se usa la plataforma y mejorarla. No registramos
            contenido de documentos subidos ni datos clínicos. Tu IP y patrones de
            uso pueden ser procesados por Google y Microsoft. Puedes cambiar tu
            decisión en cualquier momento.{" "}
            <Link
              href="/privacy"
              className="text-clinical-blue underline-offset-2 hover:underline"
            >
              Saber más
            </Link>
            .
          </p>
        </div>
        <div className="flex shrink-0 gap-2 sm:justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={handleDecline}
            data-testid="consent-decline"
          >
            <X className="size-3" />
            Rechazar
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={handleAccept}
            data-testid="consent-accept"
          >
            Aceptar
          </Button>
        </div>
      </div>
    </div>
  );
}
