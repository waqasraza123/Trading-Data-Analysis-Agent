import { AppShell } from "@/components/layout/app-shell";
import { SignalDetailView } from "@/components/signals/signal-detail-view";
import { getPublicEnv } from "@/config/env";
import { listSignalOutcomes } from "@/lib/api/outcomes";
import { getLatestSignalReadiness } from "@/lib/api/readiness";
import { getSignalAuditTimeline, getSignalReport } from "@/lib/api/reports";
import { getSignal, getSignalMarketRegime, getSignalMarketSession } from "@/lib/api/signals";
import { getSignalSetupContext } from "@/lib/api/setup-context";

type SignalPageProps = {
  params: Promise<{
    signalId: string;
  }>;
};

export default async function SignalPage({ params }: SignalPageProps) {
  const { signalId } = await params;
  const env = getPublicEnv();
  const [reportResult, signalResult, outcomesResult, readinessResult, regimeResult, sessionResult, timelineResult, setupContextResult] =
    await Promise.all([
      getSignalReport(signalId),
      getSignal(signalId),
      listSignalOutcomes(signalId),
      getLatestSignalReadiness(signalId),
      getSignalMarketRegime(signalId),
      getSignalMarketSession(signalId),
      getSignalAuditTimeline(signalId),
      getSignalSetupContext(signalId),
    ]);

  return (
    <AppShell appName={env.appName}>
      <SignalDetailView
        signal={signalResult.ok ? signalResult.data : null}
        report={reportResult.ok ? reportResult.data : null}
        outcomes={outcomesResult.ok ? outcomesResult.data : []}
        readiness={readinessResult.ok ? readinessResult.data : null}
        marketRegime={regimeResult.ok ? regimeResult.data : null}
        marketSession={sessionResult.ok ? sessionResult.data : null}
        auditTimeline={timelineResult.ok ? timelineResult.data : null}
        setupContext={setupContextResult.ok ? setupContextResult.data : null}
      />
    </AppShell>
  );
}
