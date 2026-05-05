import { Badge } from "@/components/status/badge";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatDateTime } from "@/lib/formatting/dates";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterHeader({ data }: { data: CommandCenterData }) {
  return (
    <PageHeader
      eyebrow="Daily command center"
      title="Start here"
      description="A read-only daily workflow for market memory, signal review, data readiness, scan status, outcomes, and journal follow-up."
      meta={
        <>
          <Badge value={data.workspace?.name || "No workspace"} tone="info" />
          {data.selectedPreferenceProfile && <Badge value={`Preference ${data.selectedPreferenceProfile.name}`} tone="neutral" />}
          <Badge value={`Generated ${formatDateTime(data.generatedAt)}`} />
          {data.backendUnavailable && <Badge value="Backend unavailable" tone="danger" />}
        </>
      }
      actions={
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        <SummaryPill label="Review first" value={data.summary.reviewFirstCount} />
        <SummaryPill label="Needs confirmation" value={data.summary.confirmationCount} />
        <SummaryPill label="Data ready" value={data.summary.dataReadyCount || data.summary.freshSymbolCount} />
        <SummaryPill label="Missing candles" value={data.summary.missingCandleCount} />
        <SummaryPill label="Outcome ready" value={data.summary.outcomeReadyCount} />
        <SummaryPill label="Unread events" value={data.summary.unreadNotificationCount} />
        <SummaryPill label="Quality warnings" value={data.summary.qualityWarningCount} />
      </div>
      }
    />
  );
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return <Metric label={label} value={value} />;
}
