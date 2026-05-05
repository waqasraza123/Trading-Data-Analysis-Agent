import { CommandCenterSkeleton } from "@/components/command-center/CommandCenterSkeleton";
import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";

export default function CommandCenterLoading() {
  const env = getPublicEnv();
  return (
    <AppShell appName={env.appName}>
      <CommandCenterSkeleton />
    </AppShell>
  );
}
