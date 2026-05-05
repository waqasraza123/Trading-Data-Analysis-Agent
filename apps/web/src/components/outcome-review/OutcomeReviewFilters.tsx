import { Button, ButtonLink } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewFilterShell,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
import { outcomeReviewHorizonOptions, outcomeReviewLabelOptions, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewData } from "@/lib/review/types";

export function OutcomeReviewFilters({ data }: { data: OutcomeReviewData }) {
  const selectedWorkspaceId = data.workspace?.id || data.filters.workspaceId || "";
  return (
    <form action="/review/outcomes">
      <ReviewFilterShell
        action={
          <>
            <Button variant="primary" type="submit">Apply filters</Button>
            <ButtonLink href={selectedWorkspaceId ? `/review/outcomes?workspaceId=${selectedWorkspaceId}` : "/review/outcomes"}>Reset</ButtonLink>
          </>
        }
      >
        <ReviewField label="Workspace">
          <select className={reviewInputClassName()} name="workspaceId" defaultValue={selectedWorkspaceId}>
            {data.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Symbol">
          <select className={reviewInputClassName()} name="symbolId" defaultValue={data.filters.symbolId || ""}>
            <option value="">All symbols</option>
            {data.symbols.map((symbol) => (
              <option key={symbol.id} value={symbol.id}>{symbol.symbol}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Timeframe">
          <input className={reviewInputClassName()} name="timeframe" defaultValue={data.filters.timeframe || ""} placeholder="Any" />
        </ReviewField>
        <ReviewField label="Horizon">
          <select className={reviewInputClassName()} name="horizonMinutes" defaultValue={data.filters.horizonMinutes ? String(data.filters.horizonMinutes) : ""}>
            <option value="">Any horizon</option>
            {outcomeReviewHorizonOptions.map((horizon) => (
              <option key={horizon} value={horizon}>{horizon} minutes</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Outcome">
          <select className={reviewInputClassName()} name="outcomeLabel" defaultValue={data.filters.outcomeLabel || ""}>
            <option value="">Any outcome</option>
            {outcomeReviewLabelOptions.map((label) => (
              <option key={label} value={label}>{reviewLabel(label)}</option>
            ))}
          </select>
        </ReviewField>
        <div className="flex items-end">
          <label className="flex min-h-10 w-full items-center gap-2 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm text-slate-600 dark:text-slate-300">
            <input name="onlyMissingJournal" type="checkbox" value="1" defaultChecked={data.filters.onlyMissingJournal} />
            Missing reflection note
          </label>
        </div>
      </ReviewFilterShell>
    </form>
  );
}
