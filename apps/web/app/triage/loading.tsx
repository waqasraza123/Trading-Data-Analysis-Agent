import { AppShell } from "@/components/layout/AppShell";
import { TriageSkeleton } from "@/components/triage/TriageSkeleton";
import { getPublicEnv } from "@/config/env";

export default function TriageLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <TriageSkeleton />
    </AppShell>
  );
}
