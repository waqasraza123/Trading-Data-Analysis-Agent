import Link from "next/link";
import { Badge } from "@/components/status/badge";
import type { QualityScoreboardData } from "@/lib/quality/types";

export function QualityScoreboardHeader({ data }: { data: QualityScoreboardData }) {
  const workspaceId = data.workspace?.id || "";
  return (
    <div className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Signal quality scoreboard</p>
          <h1 className="mt-1 text-2xl font-semibold text-[var(--strong)]">Observed signal quality</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Read-only analytics for deterministic signal quality, historical behavior, calibration, validation, and drift.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {data.workspace && <Badge value={data.workspace.name} tone="info" />}
          <Badge value="No financial advice" tone="neutral" />
          <Badge value="Read-only" tone="good" />
        </div>
      </div>
      <form className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4" action="/quality">
        <SelectField label="Workspace" name="workspaceId" value={workspaceId} options={data.workspaces.map((item) => ({ value: item.id, label: item.name }))} />
        <SelectField label="Strategy profile" name="strategyProfileKey" value={data.filters.strategyProfileKey || ""} options={data.filterOptions.strategyProfiles} />
        <SelectField label="Symbol" name="symbolId" value={data.filters.symbolId || ""} options={data.filterOptions.symbols} />
        <SelectField label="Timeframe" name="timeframe" value={data.filters.timeframe || ""} options={data.filterOptions.timeframes} />
        <SelectField label="Pattern" name="patternType" value={data.filters.patternType || ""} options={data.filterOptions.patterns} />
        <SelectField label="Horizon" name="horizonMinutes" value={data.filters.horizonMinutes ? String(data.filters.horizonMinutes) : ""} options={data.filterOptions.horizons} />
        <InputField label="Start date" name="startDate" value={dateValue(data.filters.startTime)} />
        <InputField label="End date" name="endDate" value={dateValue(data.filters.endTime)} />
        <div className="flex items-end gap-2 md:col-span-2 xl:col-span-4">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white" type="submit">
            Apply filters
          </button>
          <Link className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800" href={workspaceId ? `/quality?workspaceId=${workspaceId}` : "/quality"}>
            Reset
          </Link>
        </div>
      </form>
    </div>
  );
}

function SelectField({
  label,
  name,
  value,
  options,
}: {
  label: string;
  name: string;
  value: string;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
      <select
        className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm text-[var(--strong)]"
        name={name}
        defaultValue={value}
      >
        <option value="">All</option>
        {options.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function InputField({ label, name, value }: { label: string; name: string; value: string }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
      <input
        className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm text-[var(--strong)]"
        name={name}
        type="date"
        defaultValue={value}
      />
    </label>
  );
}

function dateValue(value: string | undefined): string {
  if (!value) {
    return "";
  }
  return value.slice(0, 10);
}
