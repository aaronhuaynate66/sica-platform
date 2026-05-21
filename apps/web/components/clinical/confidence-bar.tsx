import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  value: number; // 0..1
  label?: string;
  className?: string;
}

export function ConfidenceBar({ value, label, className }: ConfidenceBarProps) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  const color =
    pct >= 80
      ? "bg-confirm-green"
      : pct >= 60
        ? "bg-warn-yellow"
        : "bg-risk-red";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className={cn("absolute inset-y-0 left-0 transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
        {label ?? `${pct}%`}
      </span>
    </div>
  );
}
