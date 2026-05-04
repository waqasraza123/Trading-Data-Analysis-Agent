import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterHeader({ data }: { data: CommandCenterData }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Daily command center</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Start here</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          A read-only daily workflow for market memory, signal review, data readiness, scan status, outcomes, and journal follow-up.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge value={data.workspace?.name || "No workspace"} tone="info" />
          {data.selectedPreferenceProfile && <Badge value={`Preference ${data.selectedPreferenceProfile.name}`} tone="neutral" />}
          <Badge value={`Generated ${formatDateTime(data.generatedAt)}`} />
          {data.backendUnavailable && <Badge value="Backend unavailable" tone="danger" />}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-7">
        <SummaryPill label="Review first" value={data.summary.reviewFirstCount} />
        <SummaryPill label="Needs confirmation" value={data.summary.confirmationCount} />
        <SummaryPill label="Data ready" value={data.summary.dataReadyCount || data.summary.freshSymbolCount} />
        <SummaryPill label="Missing candles" value={data.summary.missingCandleCount} />
        <SummaryPill label="Outcome ready" value={data.summary.outcomeReadyCount} />
        <SummaryPill label="Unread events" value={data.summary.unreadNotificationCount} />
        <SummaryPill label="Quality warnings" value={data.summary.qualityWarningCount} />
      </div>
    </section>
  );
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-32 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
