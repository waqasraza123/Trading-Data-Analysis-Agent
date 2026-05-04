import { AppShell } from "@/components/layout/app-shell";
import { SetupDetailView } from "@/components/setup-detail/SetupDetailView";
import { getPublicEnv } from "@/config/env";
import { getSetupDetail } from "@/lib/api/setupDetail";

type SignalPageProps = {
  params: Promise<{
    signalId: string;
  }>;
};

export default async function SignalPage({ params }: SignalPageProps) {
  const { signalId } = await params;
  const env = getPublicEnv();
  const setupDetail = await getSetupDetail(signalId);

  return (
    <AppShell appName={env.appName}>
      <SetupDetailView data={setupDetail} />
    </AppShell>
  );
}
