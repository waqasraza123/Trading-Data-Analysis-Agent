import { Button, ButtonLink } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewFilterShell,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
import { journalDecisionTypes, journalStatuses, type JournalData } from "@/lib/journal/types";
import { reviewLabel } from "@/lib/review/labels";

export function JournalFilters({ data }: { data: JournalData }) {
  const workspaceId = data.workspace?.id || data.filters.workspaceId || "";
  const timeframes = Array.from(new Set(data.analysisRuns.map((run) => run.timeframe).filter(Boolean))).sort();
  return (
    <form action="/journal">
      <ReviewFilterShell
        action={
          <>
            <Button variant="primary" type="submit">Apply filters</Button>
            <ButtonLink href={workspaceId ? `/journal?workspaceId=${workspaceId}` : "/journal"}>Reset</ButtonLink>
          </>
        }
      >
        <ReviewField label="Workspace">
          <select className={reviewInputClassName()} name="workspaceId" defaultValue={workspaceId}>
            {data.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Decision type">
          <select className={reviewInputClassName()} name="decisionType" defaultValue={data.filters.decisionType || ""}>
            <option value="">All decision types</option>
            {journalDecisionTypes.map((decisionType) => (
              <option key={decisionType} value={decisionType}>{reviewLabel(decisionType)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Status">
          <select className={reviewInputClassName()} name="status" defaultValue={data.filters.status || ""}>
            <option value="">All statuses</option>
            {journalStatuses.map((status) => (
              <option key={status} value={status}>{reviewLabel(status)}</option>
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
          <select className={reviewInputClassName()} name="timeframe" defaultValue={data.filters.timeframe || ""}>
            <option value="">All timeframes</option>
            {timeframes.map((timeframe) => (
              <option key={timeframe} value={timeframe}>{timeframe}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Signal ID">
          <input
            className={reviewInputClassName()}
            name="signalId"
            defaultValue={data.filters.signalId || ""}
            placeholder="Optional"
          />
        </ReviewField>
      </ReviewFilterShell>
    </form>
  );
}
