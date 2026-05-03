import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefDataQualityPanel({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Data Quality" eyebrow="Freshness and warnings">
      {brief.dataQualityIssues.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.dataQuality}
          fallbackTitle="No data-quality issues"
          fallbackMessage="Freshness and setup quality warnings did not return issue rows."
        />
      ) : (
        <div className="space-y-3">
          {brief.dataQualityIssues.map((issue) => (
            <div key={issue.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{humanizeLabel(issue.label)}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {issue.symbol}
                    {issue.timeframe ? ` ${issue.timeframe}` : ""}
                  </p>
                </div>
                <Badge value={issue.severity} tone={toneForQuality(issue.severity)} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{issue.detail}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={issue.source} tone="info" />
                {issue.symbolId && brief.workspace && (
                  <Link
                    className="text-xs font-medium text-slate-500 hover:text-[var(--strong)]"
                    href={`/symbols/${issue.symbolId}?workspaceId=${brief.workspace.id}`}
                  >
                    Review symbol
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
