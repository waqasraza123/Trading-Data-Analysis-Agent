import Link from "next/link";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { humanizeLabel } from "@/lib/formatting/labels";

export function TriageFilters({ data }: { data: TriageBoardData }) {
  const filters = data.filters;
  const symbolsById = new Map(data.symbols.map((symbol) => [symbol.id, symbol]));
  const timeframes = uniqueOptions(data.allCandidates.map((candidate) => candidate.signal.signal.timeframe));
  const biases = uniqueOptions(data.allCandidates.map((candidate) => candidate.signal.signal.bias));
  const confidences = uniqueOptions(data.allCandidates.map((candidate) => candidate.signal.signal.confidence_label));
  const freshnessLabels = uniqueOptions(data.allCandidates.map((candidate) => candidate.memory?.freshness_label));
  const profileKeys = uniqueOptions(data.allCandidates.map((candidate) => candidate.signal.signal.strategy_profile_key));
  const refreshHref = buildRefreshHref(filters);

  return (
    <form action="/triage" className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Filters</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Signal triage scope</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900" type="submit">
            Apply filters
          </button>
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900" href={refreshHref}>
            Refresh
          </Link>
        </div>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Select name="workspaceId" label="Workspace" value={filters.workspaceId} options={data.workspaces.map((workspace) => ({ value: workspace.id, label: workspace.name }))} />
        <Select
          name="symbolId"
          label="Symbol"
          value={filters.symbolId}
          options={uniqueOptions(data.allCandidates.map((candidate) => candidate.signal.signal.symbol_id)).map((symbolId) => ({
            value: symbolId,
            label: symbolsById.get(symbolId)?.symbol || symbolId,
          }))}
        />
        <Select name="timeframe" label="Timeframe" value={filters.timeframe} options={timeframes.map((item) => ({ value: item, label: item }))} />
        <Select name="bias" label="Bias" value={filters.bias} options={biases.map((item) => ({ value: item, label: humanizeLabel(item) }))} />
        <Select name="confidence" label="Confidence" value={filters.confidence} options={confidences.map((item) => ({ value: item, label: humanizeLabel(item) }))} />
        <Select name="column" label="Triage column" value={filters.column} options={triageColumns.map((column) => ({ value: column.key, label: column.title }))} />
        <Select name="freshness" label="Data freshness" value={filters.freshness} options={freshnessLabels.map((item) => ({ value: item, label: humanizeLabel(item) }))} />
        <Select name="profileKey" label="Profile key" value={filters.profileKey} options={profileKeys.map((item) => ({ value: item, label: item }))} />
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-300">
        <label className="inline-flex items-center gap-2">
          <input className="h-4 w-4" defaultChecked={filters.onlyFresh} name="onlyFresh" type="checkbox" value="1" />
          Only fresh
        </label>
        <label className="inline-flex items-center gap-2">
          <input className="h-4 w-4" defaultChecked={filters.onlyReviewRequired} name="onlyReviewRequired" type="checkbox" value="1" />
          Only review required
        </label>
      </div>
    </form>
  );
}

function Select({
  label,
  name,
  value,
  options,
}: {
  label: string;
  name: string;
  value: string | undefined;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
      <select
        className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm text-[var(--strong)]"
        defaultValue={value || ""}
        name={name}
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function uniqueOptions(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function buildRefreshHref(filters: TriageBoardData["filters"]): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (typeof value === "boolean") {
      if (value) {
        params.set(key, "1");
      }
      return;
    }
    if (value) {
      params.set(key, value);
    }
  });
  params.set("loadedAt", String(Date.now()));
  return `/triage?${params.toString()}`;
}
