import { outcomeReviewHorizonOptions, outcomeReviewLabelOptions, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewData } from "@/lib/review/types";
import type { ReactNode } from "react";

export function OutcomeReviewFilters({ data }: { data: OutcomeReviewData }) {
  const selectedWorkspaceId = data.workspace?.id || data.filters.workspaceId || "";
  return (
    <form className="surface rounded-lg p-4" action="/review/outcomes">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <Select label="Workspace" name="workspaceId" defaultValue={selectedWorkspaceId}>
          {data.workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
          ))}
        </Select>
        <Select label="Symbol" name="symbolId" defaultValue={data.filters.symbolId || ""}>
          <option value="">All symbols</option>
          {data.symbols.map((symbol) => (
            <option key={symbol.id} value={symbol.id}>{symbol.symbol}</option>
          ))}
        </Select>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Timeframe</span>
          <input
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            name="timeframe"
            defaultValue={data.filters.timeframe || ""}
            placeholder="Any"
          />
        </label>
        <Select label="Horizon" name="horizonMinutes" defaultValue={data.filters.horizonMinutes ? String(data.filters.horizonMinutes) : ""}>
          <option value="">Any horizon</option>
          {outcomeReviewHorizonOptions.map((horizon) => (
            <option key={horizon} value={horizon}>{horizon} minutes</option>
          ))}
        </Select>
        <Select label="Outcome" name="outcomeLabel" defaultValue={data.filters.outcomeLabel || ""}>
          <option value="">Any outcome</option>
          {outcomeReviewLabelOptions.map((label) => (
            <option key={label} value={label}>{reviewLabel(label)}</option>
          ))}
        </Select>
        <div className="flex items-end">
          <label className="flex min-h-10 w-full items-center gap-2 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm text-slate-600 dark:text-slate-300">
            <input name="onlyMissingJournal" type="checkbox" value="1" defaultChecked={data.filters.onlyMissingJournal} />
            Missing note
          </label>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white" type="submit">
          Apply filters
        </button>
        <a className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800" href={selectedWorkspaceId ? `/review/outcomes?workspaceId=${selectedWorkspaceId}` : "/review/outcomes"}>
          Reset
        </a>
      </div>
    </form>
  );
}

function Select({
  label,
  name,
  defaultValue,
  children,
}: {
  label: string;
  name: string;
  defaultValue: string;
  children: ReactNode;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
      <select
        className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
        name={name}
        defaultValue={defaultValue}
      >
        {children}
      </select>
    </label>
  );
}
