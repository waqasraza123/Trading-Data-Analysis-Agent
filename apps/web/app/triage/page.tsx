import { AppShell } from "@/components/layout/AppShell";
import { SignalTriageBoard } from "@/components/triage/SignalTriageBoard";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getSignalTriageBoard } from "@/lib/api/triage";

type TriagePageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function TriagePage({ searchParams }: TriagePageProps) {
  const params = await searchParams;
  const data = await getSignalTriageBoard(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <SignalTriageBoard data={data} />
        </AnimatedListItem>
      </AnimatedSection>
    </AppShell>
  );
}
