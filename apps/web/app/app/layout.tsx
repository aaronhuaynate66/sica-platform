import { redirect } from "next/navigation";

import { AppSidebar } from "@/components/app/app-sidebar";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-[calc(100vh-3rem)]">
      <AppSidebar userEmail={user.email ?? null} />
      <div className="flex-1 overflow-x-hidden">{children}</div>
    </div>
  );
}
