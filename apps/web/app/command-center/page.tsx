import { CommandCenterAvoidPanel } from "@/components/command-center/CommandCenterAvoidPanel";
import { CommandCenterConfirmationPanel } from "@/components/command-center/CommandCenterConfirmationPanel";
import { CommandCenterEmptyState } from "@/components/command-center/CommandCenterEmptyState";
import { CommandCenterErrorState } from "@/components/command-center/CommandCenterErrorState";
import { CommandCenterFreshnessPanel } from "@/components/command-center/CommandCenterFreshnessPanel";
import { CommandCenterHeader } from "@/components/command-center/CommandCenterHeader";
import { CommandCenterJournalPrompt } from "@/components/command-center/CommandCenterJournalPrompt";
import { CommandCenterMorningBrief } from "@/components/command-center/CommandCenterMorningBrief";
import { CommandCenterNavigationGrid } from "@/components/command-center/CommandCenterNavigationGrid";
import { CommandCenterNextActions } from "@/components/command-center/CommandCenterNextActions";
import { CommandCenterOutcomeReview } from "@/components/command-center/CommandCenterOutcomeReview";
import { CommandCenterPrioritySetups } from "@/components/command-center/CommandCenterPrioritySetups";
import { CommandCenterScanStatus } from "@/components/command-center/CommandCenterScanStatus";
import { AppShell } from "@/components/layout/app-shell";
import { getCommandCenterData } from "@/lib/api/commandCenter";

type CommandCenterPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    preferenceProfileId?: string;
  }>;
};

export default async function CommandCenterPage({ searchParams }: CommandCenterPageProps) {
  const params = await searchParams;
  const data = await getCommandCenterData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <CommandCenterHeader data={data} />
        {!data.workspace && <CommandCenterEmptyState />}
        <CommandCenterErrorState failures={data.failures} backendUnavailable={data.backendUnavailable} />
        <CommandCenterMorningBrief data={data} />
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_390px]">
          <div className="space-y-6">
            <CommandCenterPrioritySetups data={data} />
            <CommandCenterConfirmationPanel data={data} />
            <CommandCenterOutcomeReview data={data} />
            <CommandCenterNextActions data={data} />
          </div>
          <div className="space-y-6">
            <CommandCenterFreshnessPanel data={data} />
            <CommandCenterAvoidPanel data={data} />
            <CommandCenterScanStatus data={data} />
            <CommandCenterJournalPrompt data={data} />
          </div>
        </div>
        <CommandCenterNavigationGrid data={data} />
      </div>
    </AppShell>
  );
}
