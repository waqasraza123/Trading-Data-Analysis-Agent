import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { cn } from "@/lib/ui/cn";

type RouteLoadingShellProps = {
  children: ReactNode;
  className?: string;
  workspaceId?: string | null;
  workspaceName?: string | null;
};

export function RouteLoadingShell({
  children,
  className,
  workspaceId,
  workspaceName,
}: RouteLoadingShellProps) {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName} workspaceId={workspaceId} workspaceName={workspaceName}>
      <section className={cn("space-y-6", className)}>{children}</section>
    </AppShell>
  );
}
