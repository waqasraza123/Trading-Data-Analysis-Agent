import { AppShell } from "@/components/layout/AppShell";
import { OnboardingSkeleton } from "@/components/onboarding/OnboardingSkeleton";
import { getPublicEnv } from "@/config/env";

export default function OnboardingLoading() {
  const env = getPublicEnv();
  return (
    <AppShell appName={env.appName}>
      <OnboardingSkeleton />
    </AppShell>
  );
}
