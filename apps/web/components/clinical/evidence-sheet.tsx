"use client";

import { FileText } from "lucide-react";
import type { ReactElement } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { EvidenceSpan } from "@/lib/types/obstetric-summary";

interface EvidenceSheetProps {
  trigger?: ReactElement;
  title: string;
  spans: EvidenceSpan[];
}

export function EvidenceSheet({ trigger, title, spans }: EvidenceSheetProps) {
  const triggerNode: ReactElement = trigger ?? (
    <Button variant="ghost" size="xs" className="gap-1">
      <FileText className="size-3" />
      Ver evidencia
    </Button>
  );

  return (
    <Sheet>
      <SheetTrigger render={triggerNode} />
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>
            Spans literales copiados del documento fuente. No parafrasear.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-3 overflow-y-auto px-4 pb-6">
          {spans.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin evidencia explícita asociada a este campo.
            </p>
          ) : (
            spans.map((span, idx) => (
              <div
                key={idx}
                className="rounded-md border border-border bg-muted/30 p-3"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-medium text-foreground">
                    {span.claim}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    p. {span.source_page}
                  </span>
                </div>
                <pre className="whitespace-pre-wrap font-mono text-[11px] text-muted-foreground">
                  {span.source_text}
                </pre>
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
