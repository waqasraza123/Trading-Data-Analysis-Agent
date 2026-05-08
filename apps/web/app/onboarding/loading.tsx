import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { OnboardingSkeleton } from "@/components/onboarding/OnboardingSkeleton";

export default function OnboardingLoading() {
  return (
    <RouteLoadingShell>
      <OnboardingSkeleton />
    </RouteLoadingShell>
  );
}
