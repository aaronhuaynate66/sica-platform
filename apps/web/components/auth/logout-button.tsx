"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";

interface LogoutButtonProps {
  variant?: "default" | "ghost" | "outline";
  size?: "sm" | "default";
  showLabel?: boolean;
}

export function LogoutButton({
  variant = "ghost",
  size = "sm",
  showLabel = true,
}: LogoutButtonProps) {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
    } finally {
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      onClick={handleLogout}
      disabled={signingOut}
    >
      {signingOut ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <LogOut className="size-4" />
      )}
      {showLabel && <span className="ml-2">Cerrar sesión</span>}
    </Button>
  );
}
