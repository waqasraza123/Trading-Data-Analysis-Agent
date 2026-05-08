import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { cn } from "@/lib/ui/cn";

type RouteLoadingShellProps = {
  children: ReactNode;
  className?: string;
};

export function RouteLoadingShell({ children, className }: RouteLoadingShellProps) {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className={cn("space-y-6", className)}>{children}</section>
    </AppShell>
  );
}
