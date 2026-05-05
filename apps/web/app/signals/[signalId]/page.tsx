import { AppShell } from "@/components/layout/AppShell";
import { SetupReviewView } from "@/components/setup-review/SetupReviewView";
import { getPublicEnv } from "@/config/env";
import { getSetupReview } from "@/lib/api/setupReview";

type SignalPageProps = {
  params: Promise<{
    signalId: string;
  }>;
};

export default async function SignalPage({ params }: SignalPageProps) {
  const { signalId } = await params;
  const env = getPublicEnv();
  const setupReview = await getSetupReview(signalId);

  return (
    <AppShell appName={env.appName}>
      <SetupReviewView data={setupReview} />
    </AppShell>
  );
}
