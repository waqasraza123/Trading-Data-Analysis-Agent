import { AppShell } from "@/components/layout/AppShell";
import { SetupReviewView } from "@/components/setup-review/SetupReviewView";
import { getPublicEnv } from "@/config/env";
import { getSetupReview } from "@/lib/api/setupReview";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";

type SignalPageProps = {
  params: Promise<{
    signalId: string;
  }>;
};

export default async function SignalPage({ params }: SignalPageProps) {
  const { signalId } = await params;
  const env = getPublicEnv();
  const setupReview = await getSetupReview(signalId);
  const workspaceId =
    setupReview.signal?.signal.workspace_id ||
    setupReview.report?.workspace_id ||
    setupReview.setupContext?.workspace_id ||
    null;

  return (
    <AppShell appName={env.appName} workspaceId={workspaceId}>
      <AnimatedSection as="section">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <SetupReviewView data={setupReview} />
        </AnimatedListItem>
      </AnimatedSection>
    </AppShell>
  );
}
