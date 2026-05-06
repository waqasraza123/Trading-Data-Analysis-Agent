import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";
import { CockpitMetric, CockpitPanel } from "./CommandCenterCockpitPrimitives";

export function CommandCenterNotificationJournal({ overview }: { overview: WorkspaceOverview }) {
  return (
    <CockpitPanel title="Notifications And Journal" eyebrow="Inbox and reflection">
      <div className="grid gap-3 sm:grid-cols-2">
        <CockpitMetric label="Unread inbox" value={overview.notifications.unread_count} tone={overview.notifications.unread_count ? "info" : "neutral"} />
        <CockpitMetric label="Journal prompts" value={overview.journal_prompts.length} tone={overview.journal_prompts.length ? "warning" : "neutral"} />
      </div>
      <div className="mt-4">
        <CommandCenterOverviewItemList title="Journal Prompts" eyebrow="Reflection" items={overview.journal_prompts} empty="No journal prompts from overview." workspaceId={overview.workspace_id} />
      </div>
    </CockpitPanel>
  );
}
