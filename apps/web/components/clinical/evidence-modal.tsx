"use client";

import { ExternalLink, FileText, X } from "lucide-react";

import { applyMaskingProps } from "@/lib/analytics/masking";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { EvidenceSpan } from "@/lib/types/obstetric-summary";

interface EvidenceModalProps {
  /** Spans que respaldan el campo. Vacío => mensaje "sin evidencia". */
  evidence: EvidenceSpan[];
  /** Nombre legible del campo, va al header. */
  fieldName: string;
  /** URL del PDF para abrir en página específica. null en uploads en vivo. */
  pdfUrl: string | null;
  /**
   * Trigger custom. Si se omite, se renderiza un botón ghost compacto con
   * el ícono FileText + texto "Ver evidencia".
   */
  trigger?: React.ReactNode;
}

export function EvidenceModal({ evidence, fieldName, pdfUrl, trigger }: EvidenceModalProps) {
  const hasEvidence = evidence.length > 0;
  const triggerNode = trigger ?? (
    <Button
      variant="ghost"
      size="xs"
      className="gap-1"
      aria-label={`Ver evidencia de ${fieldName}`}
      disabled={!hasEvidence}
      title={hasEvidence ? "Ver evidencia trazable" : "Sin evidencia trazable disponible"}
    >
      <FileText className="size-3" />
      Ver evidencia
    </Button>
  );

  return (
    <Dialog>
      <DialogTrigger render={triggerNode as React.ReactElement} />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="size-4 text-clinical-blue" />
            Evidencia: {fieldName}
          </DialogTitle>
          <DialogDescription>
            Fragmentos literales copiados del documento fuente. No parafrasear.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 max-h-[60vh] overflow-y-auto" data-testid="evidence-list">
          {!hasEvidence ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Sin evidencia explícita asociada a este campo.
            </p>
          ) : (
            evidence.map((span, idx) => (
              <article
                key={`${span.source_page}-${idx}`}
                {...applyMaskingProps()}
                className="rounded-md border border-border bg-muted/30 p-3"
                data-testid="evidence-item"
              >
                <header className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-medium text-foreground">{span.claim}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    p. {span.source_page}
                  </span>
                </header>
                <pre
                  {...applyMaskingProps()}
                  className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-foreground"
                >
                  {span.source_text}
                </pre>
                {pdfUrl ? (
                  <a
                    href={`${pdfUrl}#page=${span.source_page}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-[11px] text-clinical-blue hover:underline"
                    data-testid="open-pdf-link"
                  >
                    <ExternalLink className="size-3" />
                    Abrir PDF en página {span.source_page}
                  </a>
                ) : (
                  <p className="mt-2 text-[10px] text-muted-foreground italic">
                    PDF subido vive sólo en memoria — no se persiste anchor a página.
                  </p>
                )}
              </article>
            ))
          )}
        </div>

        <DialogFooter>
          <DialogClose render={<Button variant="outline" size="sm" />}>
            <X className="size-3" />
            Cerrar
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
