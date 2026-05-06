import type { CommandCenterData } from "@/lib/command-center/types";
import { CommandCenterAvoidConditions } from "./CommandCenterAvoidConditions";
import { CommandCenterMissingSections } from "./CommandCenterMissingSections";
import { CommandCenterNeedsConfirmation } from "./CommandCenterNeedsConfirmation";
import { CommandCenterNotificationJournal } from "./CommandCenterNotificationJournal";
import { CommandCenterOutcomeUpdates } from "./CommandCenterOutcomeUpdates";
import { CommandCenterQualityWarnings } from "./CommandCenterQualityWarnings";
import { CommandCenterQuickActions } from "./CommandCenterQuickActions";
import { CommandCenterReadinessStrip } from "./CommandCenterReadinessStrip";
import { CommandCenterReviewFirst } from "./CommandCenterReviewFirst";
import { CommandCenterWorkflowStatus } from "./CommandCenterWorkflowStatus";

export function CommandCenterOverview({ data }: { data: CommandCenterData }) {
  const overview = data.workspaceOverview;
  if (!overview) {
    return null;
  }
  return (
    <section className="space-y-5">
      <CommandCenterReadinessStrip overview={overview} />
      <CommandCenterQuickActions
        workspaceId={data.workspace?.id || overview.workspace_id}
        watchlistId={data.dailyWorkflowDefaultWatchlistId}
        preferenceProfileId={data.selectedPreferenceProfile?.id || null}
      />
      <CommandCenterMissingSections overview={overview} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
        <div className="space-y-5">
          <CommandCenterReviewFirst overview={overview} />
          <CommandCenterNeedsConfirmation overview={overview} />
          <div className="grid gap-5 2xl:grid-cols-2">
            <CommandCenterAvoidConditions overview={overview} />
            <CommandCenterOutcomeUpdates overview={overview} />
          </div>
        </div>
        <div className="space-y-5">
          <CommandCenterWorkflowStatus overview={overview} />
          <CommandCenterNotificationJournal overview={overview} />
          <CommandCenterQualityWarnings overview={overview} />
        </div>
      </div>
    </section>
  );
}
