import { Button, ButtonLink } from "@/components/ui/Button";
import { FilterBar } from "@/components/ui/FilterBar";
import { Badge } from "@/components/ui/Badge";
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
  const activeFilters = Object.entries(filters).filter(([key, value]) => Boolean(value) && !(key === "sort" && value === "priority"));

  return (
    <form action="/triage" className="sticky top-24 z-10">
      <FilterBar
        title="Review board filters"
        actions={
          <>
            <Button variant="primary" type="submit">Apply filters</Button>
            <ButtonLink href={refreshHref}>Refresh</ButtonLink>
          </>
        }
      >
        <SearchInput name="symbolSearch" label="Search symbol" value={filters.symbolSearch} />
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
        <Select
          name="preferenceProfileId"
          label="Preference profile"
          value={filters.preferenceProfileId}
          options={data.preferenceProfiles.map((profile) => ({
            value: profile.id,
            label: profile.is_default ? `${profile.name} (default)` : profile.name,
          }))}
        />
        <Select
          name="sort"
          label="Sort"
          value={filters.sort || "priority"}
          options={[
            { value: "priority", label: "Priority score" },
            { value: "freshness", label: "Freshness" },
            { value: "confidence", label: "Confidence" },
            { value: "created", label: "Created time" },
          ]}
        />
      <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-300 md:col-span-2 xl:col-span-4">
        <label className="inline-flex items-center gap-2">
          <input className="h-4 w-4" defaultChecked={filters.onlyFresh} name="onlyFresh" type="checkbox" value="1" />
          Only fresh
        </label>
        <label className="inline-flex items-center gap-2">
          <input className="h-4 w-4" defaultChecked={filters.onlyReviewRequired} name="onlyReviewRequired" type="checkbox" value="1" />
          Only review required
        </label>
      </div>
      {activeFilters.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 md:col-span-2 xl:col-span-4">
          {activeFilters.slice(0, 8).map(([key, value]) => (
            <Badge key={key} value={`${humanizeLabel(key)}: ${value === true ? "Yes" : String(value)}`} tone="info" />
          ))}
        </div>
      )}
      </FilterBar>
    </form>
  );
}

function SearchInput({ label, name, value }: { label: string; name: string; value: string | undefined }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
      <input
        className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm text-[var(--strong)]"
        defaultValue={value || ""}
        name={name}
        placeholder="BTC, ETH, SPY"
      />
    </label>
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
