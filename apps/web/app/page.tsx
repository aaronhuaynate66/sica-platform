"use client";

import { FileUp, Loader2, Play, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EditableSummaryView } from "@/components/clinical/editable-summary-view";
import {
  syntheticCase01PdfPath,
  syntheticCase01Summary,
} from "@/lib/fixtures";
import { extractFromPdf } from "@/lib/api/client";
import { getConfiguredMode, isApiAvailable } from "@/lib/api/mode-detector";
import {
  ApiError,
  ApiTimeoutError,
  ApiUnavailableError,
  type ObstetricSummary,
} from "@/lib/api/types";

type DisplayState =
  | { kind: "empty" }
  | { kind: "demo"; summary: ObstetricSummary; pdfPath: string; label: string }
  | { kind: "live"; summary: ObstetricSummary; pdfPath: string; label: string }
  | { kind: "loading"; label: string }
  | { kind: "error"; message: string };

export default function UploadAndExtractPage() {
  const configuredMode = getConfiguredMode();
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [display, setDisplay] = useState<DisplayState>({ kind: "empty" });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastObjectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (configuredMode === "demo") {
      setApiUp(false);
      return;
    }
    let cancelled = false;
    isApiAvailable({ forceFresh: true }).then((ok) => {
      if (!cancelled) setApiUp(ok);
    });
    return () => {
      cancelled = true;
    };
  }, [configuredMode]);

  const effectiveMode: "live" | "demo" =
    configuredMode === "live" && apiUp === true ? "live" : "demo";

  const loadDemo = useCallback(() => {
    setDisplay({
      kind: "demo",
      summary: syntheticCase01Summary,
      pdfPath: syntheticCase01PdfPath,
      label: "synthetic_case_01.pdf",
    });
  }, []);

  const triggerUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      if (effectiveMode === "demo") {
        setDisplay({
          kind: "error",
          message:
            "Modo demo: subir PDFs propios requiere API conectada. Usa el ejemplo o solicita acceso.",
        });
        return;
      }

      if (lastObjectUrlRef.current) {
        URL.revokeObjectURL(lastObjectUrlRef.current);
        lastObjectUrlRef.current = null;
      }

      setDisplay({ kind: "loading", label: file.name });
      try {
        const summary = await extractFromPdf(file);
        const objectUrl = URL.createObjectURL(file);
        lastObjectUrlRef.current = objectUrl;
        setDisplay({
          kind: "live",
          summary,
          pdfPath: objectUrl,
          label: file.name,
        });
      } catch (err) {
        let message: string;
        if (err instanceof ApiTimeoutError) {
          message =
            "La extracción excedió el tiempo máximo (60s). Probá con un PDF más corto.";
        } else if (err instanceof ApiUnavailableError) {
          message = "No se pudo conectar al backend. Confirmá que sica-api está corriendo.";
        } else if (err instanceof ApiError) {
          message = `Error ${err.status} (${err.code}): ${err.message}`;
        } else {
          message = "Error inesperado procesando el documento.";
        }
        setDisplay({ kind: "error", message });
      }
    },
    [effectiveMode],
  );

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = ""; // reset for re-selection of same file
      if (file) void handleFile(file);
    },
    [handleFile],
  );

  useEffect(() => {
    return () => {
      if (lastObjectUrlRef.current) {
        URL.revokeObjectURL(lastObjectUrlRef.current);
      }
    };
  }, []);

  const modeBadge =
    effectiveMode === "live" ? (
      <Badge variant="outline" className="border-confirm-green/50 text-confirm-green">
        ● Live mode
      </Badge>
    ) : (
      <Badge variant="outline" className="border-warn-yellow/50 text-warn-yellow">
        ● Demo mode
      </Badge>
    );

  return (
    <div className="flex flex-col">
      <div className="border-b border-border bg-muted/20 px-6 py-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">SICA — Demo interna</h1>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              Carga una historia clínica obstétrica y SICA la transforma en un resumen estructurado
              con evidencia trazable. Esta demo usa{" "}
              <strong className="text-foreground">datos sintéticos</strong> por defecto. En modo
              live el backend procesa el PDF real que subas.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={loadDemo} variant="default" size="sm">
                <Play className="size-3.5" />
                Cargar PDF de ejemplo
              </Button>
              <Button onClick={triggerUpload} variant="outline" size="sm">
                <FileUp className="size-3.5" />
                Subir PDF propio
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,.pdf"
                onChange={onFileChange}
                className="hidden"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            {modeBadge}
            <Badge variant="outline" className="font-mono">
              caso demo
            </Badge>
            <Badge variant="outline" className="border-warn-yellow/50 text-warn-yellow">
              sintético
            </Badge>
          </div>
        </div>
      </div>

      {display.kind === "empty" && (
        <div className="flex-1 flex items-center justify-center px-6 py-16 text-center">
          <div className="max-w-md">
            <p className="text-sm text-muted-foreground">
              Pulsá <strong className="text-foreground">Cargar PDF de ejemplo</strong> para ver una
              extracción sintética pre-procesada, o{" "}
              <strong className="text-foreground">Subir PDF propio</strong> si tenés modo live
              activo.
            </p>
            <p className="mt-3 text-[11px] text-muted-foreground/70">
              Modo configurado: <code className="font-mono">{configuredMode}</code>
              {configuredMode === "live" && apiUp === false && (
                <>
                  {" · "}
                  <span className="text-warn-yellow">
                    API no respondió en /health; cayendo a demo.
                  </span>
                </>
              )}
            </p>
          </div>
        </div>
      )}

      {display.kind === "loading" && (
        <div className="flex-1 flex items-center justify-center px-6 py-16 text-center">
          <div className="max-w-md">
            <Loader2 className="mx-auto size-8 animate-spin text-clinical-blue" />
            <p className="mt-3 text-sm font-medium">
              Procesando <code className="font-mono">{display.label}</code>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Puede tomar entre 10 y 30 segundos.
            </p>
          </div>
        </div>
      )}

      {display.kind === "error" && (
        <div className="flex-1 flex items-center justify-center px-6 py-16 text-center">
          <div className="max-w-md">
            <p className="text-sm font-medium text-risk-red">{display.message}</p>
            <Button
              onClick={() => setDisplay({ kind: "empty" })}
              variant="outline"
              size="sm"
              className="mt-4"
            >
              <RefreshCw className="size-3.5" />
              Reintentar
            </Button>
          </div>
        </div>
      )}

      {(display.kind === "demo" || display.kind === "live") && (
        <EditableSummaryView
          // Re-mount cuando cambia el case → reset del estado editable.
          key={`${display.kind}:${display.label}`}
          initialSummary={display.summary}
          pdfPath={display.pdfPath}
          pdfLabel={display.label}
          origin={display.kind}
        />
      )}
    </div>
  );
}
