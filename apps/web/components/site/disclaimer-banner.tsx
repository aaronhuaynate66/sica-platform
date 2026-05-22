import { AlertTriangle, Pencil } from "lucide-react";
import Link from "next/link";

export function DisclaimerBanner() {
  return (
    <div className="sticky bottom-0 z-50 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-9 items-center gap-2 px-6 text-xs text-muted-foreground">
        <AlertTriangle className="size-3.5 text-warn-yellow shrink-0" />
        <span className="font-medium">Datos sintéticos</span>
        <span className="opacity-60">·</span>
        <span>No es paciente real</span>
        <span className="opacity-60">·</span>
        <span>No clínicamente validado</span>
        <span className="opacity-60 hidden md:inline">·</span>
        <span
          className="hidden md:inline-flex items-center gap-1"
          title="Las ediciones manuales viven sólo en la sesión actual. Persistencia y feedback formal vienen en la próxima versión."
        >
          <Pencil className="size-3 text-clinical-blue" />
          Ediciones en memoria
        </span>
        <span className="ml-auto flex items-center gap-3">
          <Link
            href="/privacy"
            className="hover:text-foreground underline-offset-2 hover:underline"
          >
            Privacidad
          </Link>
        </span>
      </div>
    </div>
  );
}
