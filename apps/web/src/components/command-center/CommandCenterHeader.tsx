import { Badge } from "@/components/status/badge";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { formatDateTime } from "@/lib/formatting/dates";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterHeader({ data }: { data: CommandCenterData }) {
  const heroPills = [
    { label: "Review first", value: data.summary.reviewFirstCount },
    { label: "Needs confirmation", value: data.summary.confirmationCount },
    { label: "Data ready", value: data.summary.dataReadyCount || data.summary.freshSymbolCount },
    { label: "Missing candles", value: data.summary.missingCandleCount },
    { label: "Outcome ready", value: data.summary.outcomeReadyCount },
    { label: "Unread events", value: data.summary.unreadNotificationCount },
    { label: "Quality warnings", value: data.summary.qualityWarningCount },
  ];

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
        <div className={`grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7 ${motionRevealPresetClass()}`}>
          {heroPills.map((pill, index) => (
            <AnimatedListItem key={pill.label} as="article" style={motionRevealDensityStyle(index, "compact")}>
              <SummaryPill label={pill.label} value={pill.value} />
            </AnimatedListItem>
          ))}
        </div>
      }
    />
  );
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return <Metric label={label} value={value} className={motionCardClass} />;
}
