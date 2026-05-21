import { AlertTriangle } from "lucide-react";

export function DisclaimerBanner() {
  return (
    <div className="sticky bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-9 items-center gap-2 px-6 text-xs text-muted-foreground">
        <AlertTriangle className="size-3.5 text-warn-yellow" />
        <span className="font-medium">Datos sintéticos</span>
        <span className="opacity-60">·</span>
        <span>No es paciente real</span>
        <span className="opacity-60">·</span>
        <span>No clínicamente validado</span>
      </div>
    </div>
  );
}
