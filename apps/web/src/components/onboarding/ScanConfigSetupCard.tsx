import type { OnboardingActionType, OnboardingStep } from "@/lib/onboarding/types";
import { OnboardingStepCard } from "./OnboardingStepCard";

export function ScanConfigSetupCard(props: {
  step: OnboardingStep;
  workspaceId?: string | null;
  pending?: boolean;
  onAction: (actionType: OnboardingActionType) => void;
}) {
  return <OnboardingStepCard {...props} />;
}
