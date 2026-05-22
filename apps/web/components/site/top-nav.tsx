"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/site/theme-toggle";
import { ANALYTICS_EVENTS } from "@/lib/analytics/events";
import { useAnalytics } from "@/lib/analytics/use-analytics";

const NAV_ITEMS = [
  { href: "/", label: "Upload" },
  { href: "/timeline", label: "Timeline" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/physician", label: "Physician" },
] as const;

export function TopNav() {
  const pathname = usePathname();
  const { trackEvent } = useAnalytics();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-12 items-center gap-6 px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Activity className="size-5 text-clinical-blue" />
          <span>SICA</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => {
                  if (item.href !== pathname) {
                    trackEvent(ANALYTICS_EVENTS.VIEW_CHANGED, {
                      from: pathname,
                      to: item.href,
                    });
                  }
                }}
                className={cn(
                  "rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive && "bg-muted text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <Badge variant="outline" className="font-mono text-[10px]">
            v0.1.0 · Demo
          </Badge>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
