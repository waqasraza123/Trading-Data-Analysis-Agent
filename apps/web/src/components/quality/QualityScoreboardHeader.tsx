import { Badge } from "@/components/status/badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewFilterShell,
  ReviewSurfaceHero,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
import type { QualityScoreboardData } from "@/lib/quality/types";

export function QualityScoreboardHeader({ data }: { data: QualityScoreboardData }) {
  const workspaceId = data.workspace?.id || "";
  return (
    <div className="space-y-5">
      <ReviewSurfaceHero
        eyebrow="Daily quality review"
        title="Quality dashboard"
        description="Read-only diagnostics for confidence alignment, drift, walk-forward stability, pattern attribution, profile reliability, and sample coverage."
        actions={
          <>
          {data.workspace && <Badge value={data.workspace.name} tone="info" />}
          <Badge value="No financial advice" tone="neutral" />
          <Badge value="Read-only" tone="good" />
        </>
        }
      />
      <form action="/quality">
        <ReviewFilterShell
          action={
            <>
              <Button variant="primary" type="submit">Apply filters</Button>
              <ButtonLink href={workspaceId ? `/quality?workspaceId=${workspaceId}` : "/quality"}>Reset</ButtonLink>
            </>
          }
        >
        <SelectField label="Workspace" name="workspaceId" value={workspaceId} options={data.workspaces.map((item) => ({ value: item.id, label: item.name }))} />
        <SelectField label="Strategy profile" name="strategyProfileKey" value={data.filters.strategyProfileKey || ""} options={data.filterOptions.strategyProfiles} />
        <SelectField label="Symbol" name="symbolId" value={data.filters.symbolId || ""} options={data.filterOptions.symbols} />
        <SelectField label="Timeframe" name="timeframe" value={data.filters.timeframe || ""} options={data.filterOptions.timeframes} />
        <SelectField label="Pattern" name="patternType" value={data.filters.patternType || ""} options={data.filterOptions.patterns} />
        <SelectField label="Horizon" name="horizonMinutes" value={data.filters.horizonMinutes ? String(data.filters.horizonMinutes) : ""} options={data.filterOptions.horizons} />
        <InputField label="Start date" name="startDate" value={dateValue(data.filters.startTime)} />
        <InputField label="End date" name="endDate" value={dateValue(data.filters.endTime)} />
        </ReviewFilterShell>
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
    <ReviewField label={label}>
      <select
        className={reviewInputClassName()}
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
    </ReviewField>
  );
}

function InputField({ label, name, value }: { label: string; name: string; value: string }) {
  return (
    <ReviewField label={label}>
      <input
        className={reviewInputClassName()}
        name={name}
        type="date"
        defaultValue={value}
      />
    </ReviewField>
  );
}

function dateValue(value: string | undefined): string {
  if (!value) {
    return "";
  }
  return value.slice(0, 10);
}
