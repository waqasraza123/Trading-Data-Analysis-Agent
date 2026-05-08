import type { ReactNode } from "react";
import { getPublicEnv } from "@/config/env";
import { PageContainer } from "./PageContainer";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { cn } from "@/lib/ui/cn";
import { AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";

type AppShellProps = {
  appName: string;
  children: ReactNode;
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function AppShell({ appName, children, workspaceName, workspaceId }: AppShellProps) {
  const env = getPublicEnv();

  return (
    <AnimatedSection
      as="div"
      preset="fade-up"
      className={cn("min-h-screen bg-transparent text-[var(--foreground)]")}
      style={motionRevealDensityStyle(0, "regular")}
    >
      <div className="fixed inset-x-0 top-0 z-40 lg:hidden">
        <MobileNav appName={appName} workspaceId={workspaceId} workspaceName={workspaceName} apiBaseUrl={env.apiBaseUrl} />
      </div>
      <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:block lg:w-72 lg:p-4">
        <Sidebar appName={appName} workspaceId={workspaceId} workspaceName={workspaceName} />
      </div>
      <div className="min-h-screen pt-20 lg:pl-72 lg:pt-0">
        <Topbar apiBaseUrl={env.apiBaseUrl} workspaceId={workspaceId} workspaceName={workspaceName} />
        <PageContainer>{children}</PageContainer>
      </div>
    </AnimatedSection>
  );
}
