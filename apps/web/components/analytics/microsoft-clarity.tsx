"use client";

import Script from "next/script";

import { useConsent } from "@/lib/analytics/use-consent";

/**
 * Carga el tag de Microsoft Clarity sólo cuando:
 *  1) NEXT_PUBLIC_CLARITY_PROJECT_ID está definido y no vacío en el build, Y
 *  2) el usuario aceptó analytics en el ConsentBanner.
 *
 * Clarity captura grabaciones de sesión + heatmaps. Por defecto enmascara
 * inputs y elementos con `data-clarity-mask="true"`. Ver
 * `lib/analytics/masking.ts` para los elementos que llevan el atributo.
 */
export function MicrosoftClarity() {
  const projectId = process.env.NEXT_PUBLIC_CLARITY_PROJECT_ID;
  const { consent } = useConsent();

  if (!projectId || projectId.trim() === "") return null;
  if (consent !== "granted") return null;

  return (
    <Script id="clarity-init" strategy="afterInteractive">
      {`
        (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
        })(window, document, "clarity", "script", "${projectId}");
      `}
    </Script>
  );
}
