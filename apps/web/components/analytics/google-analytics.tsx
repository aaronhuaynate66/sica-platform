"use client";

import Script from "next/script";

import { useConsent } from "@/lib/analytics/use-consent";

/**
 * Carga gtag.js de Google Analytics 4 sólo cuando:
 *  1) NEXT_PUBLIC_GA_MEASUREMENT_ID está definido y no vacío en el build, Y
 *  2) el usuario aceptó analytics en el ConsentBanner.
 *
 * Notas regulatorias:
 *  - `anonymize_ip: true` es obligatorio bajo Ley 29733 — Google trunca el
 *    último octeto antes de almacenar.
 *  - El script se inyecta con strategy="afterInteractive" para no bloquear
 *    el render inicial.
 *  - Cualquier dato extraído (PHI) tiene `data-no-track="true"` y nuestro
 *    `trackEvent` filtra params sospechosos — pero la defensa principal es
 *    no enviar PHI en eventos.
 */
export function GoogleAnalytics() {
  const measurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
  const { consent } = useConsent();

  if (!measurementId || measurementId.trim() === "") return null;
  if (consent !== "granted") return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`}
        strategy="afterInteractive"
      />
      <Script id="ga-init" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          window.gtag = gtag;
          gtag('js', new Date());
          gtag('config', '${measurementId}', {
            anonymize_ip: true,
            send_page_view: true
          });
        `}
      </Script>
    </>
  );
}
