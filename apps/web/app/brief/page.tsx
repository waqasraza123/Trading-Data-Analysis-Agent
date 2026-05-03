import { BriefAvoidConditions } from "@/components/brief/BriefAvoidConditions";
import { BriefDataQualityPanel } from "@/components/brief/BriefDataQualityPanel";
import { BriefDigestSummaries } from "@/components/brief/BriefDigestSummaries";
import { BriefErrorState } from "@/components/brief/BriefErrorState";
import { BriefHeader } from "@/components/brief/BriefHeader";
import { BriefMarketFocus } from "@/components/brief/BriefMarketFocus";
import { BriefOutcomeUpdates } from "@/components/brief/BriefOutcomeUpdates";
import { BriefPendingActions } from "@/components/brief/BriefPendingActions";
import { BriefReviewNeededPanel } from "@/components/brief/BriefReviewNeededPanel";
import { BriefSetupList } from "@/components/brief/BriefSetupList";
import { BriefSummaryCards } from "@/components/brief/BriefSummaryCards";
import { BriefWatchNextPanel } from "@/components/brief/BriefWatchNextPanel";
import { EmptyState } from "@/components/empty-states/empty-state";
import { AppShell } from "@/components/layout/app-shell";
import { getWorkspaceBrief } from "@/lib/api/brief";

type BriefPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function BriefPage({ searchParams }: BriefPageProps) {
  const params = await searchParams;
  const brief = await getWorkspaceBrief(params);

  return (
    <AppShell appName={brief.appName}>
      <div className="space-y-6">
        <BriefHeader brief={brief} />
        <BriefErrorState brief={brief} />
        {!brief.workspace && (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before the workspace brief can load."
          />
        )}
        <BriefSummaryCards brief={brief} />
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_390px]">
          <div className="space-y-6">
            <BriefMarketFocus brief={brief} />
            <BriefSetupList brief={brief} />
            <BriefOutcomeUpdates brief={brief} />
          </div>
          <aside className="space-y-6">
            <BriefAvoidConditions brief={brief} />
            <BriefDataQualityPanel brief={brief} />
            <BriefWatchNextPanel brief={brief} />
            <BriefReviewNeededPanel brief={brief} />
            <BriefPendingActions brief={brief} />
            <BriefDigestSummaries brief={brief} />
          </aside>
        </div>
      </div>
    </AppShell>
  );
}
