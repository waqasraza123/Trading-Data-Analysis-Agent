import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/empty-states/empty-state";
import { JournalPromptPanel } from "@/components/review/JournalPromptPanel";
import { OutcomeReviewErrorState } from "@/components/review/OutcomeReviewErrorState";
import { OutcomeReviewFilters } from "@/components/review/OutcomeReviewFilters";
import { OutcomeReviewHeader } from "@/components/review/OutcomeReviewHeader";
import { OutcomeReviewQueue } from "@/components/review/OutcomeReviewQueue";
import { OutcomeSummaryPanel } from "@/components/review/OutcomeSummaryPanel";
import { PatternDegradationPanel } from "@/components/review/PatternDegradationPanel";
import { ProfileReliabilityPanel } from "@/components/review/ProfileReliabilityPanel";
import { getOutcomeReviewData } from "@/lib/api/outcomeReview";

type OutcomeReviewPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function OutcomeReviewPage({ searchParams }: OutcomeReviewPageProps) {
  const params = await searchParams;
  const data = await getOutcomeReviewData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <OutcomeReviewHeader data={data} />
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before the outcome review loop can load."
          />
        ) : (
          <>
            <OutcomeSummaryPanel data={data} />
            <OutcomeReviewFilters data={data} />
            <OutcomeReviewErrorState failures={data.failures} />
            <JournalPromptPanel items={data.queue} workspaceId={data.workspace.id} />
            <ProfileReliabilityPanel data={data} />
            <PatternDegradationPanel data={data} />
            <OutcomeReviewQueue data={data} />
          </>
        )}
      </div>
    </AppShell>
  );
}
