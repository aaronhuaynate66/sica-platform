"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Upload, Users } from "lucide-react";

import { cn } from "@/lib/utils";
import { LogoutButton } from "@/components/auth/logout-button";

interface AppSidebarProps {
  userEmail: string | null;
}

const NAV_ITEMS = [
  { href: "/app", label: "Pacientes", icon: Users, exact: true },
  { href: "/app/upload", label: "Subir control", icon: Upload, exact: false },
] as const;

export function AppSidebar({ userEmail }: AppSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <Activity className="size-5 text-clinical-blue" />
        <span className="font-semibold tracking-tight">SICA</span>
        <span className="ml-auto rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          R1
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.exact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                isActive && "bg-muted text-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3">
        {userEmail && (
          <p className="mb-2 truncate text-xs text-muted-foreground" title={userEmail}>
            {userEmail}
          </p>
        )}
        <LogoutButton variant="outline" size="sm" />
      </div>
    </aside>
  );
}
