import { useState } from "react";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { DataSource } from "@/lib/data-onboarding/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type DataSourceStepProps = {
  dataSources: DataSource[];
  selectedSourceId: string | null;
  loadState: string;
  onSourceChange: (sourceId: string) => void;
  onCreateSource: (payload: { name: string; sourceType: string; provider: string }) => void;
};

const sourceTypeOptions = [
  { value: "csv_upload", label: "csv_upload" },
  { value: "json_import", label: "json_import" },
  { value: "api_polling", label: "provider_polling" },
  { value: "websocket_live", label: "websocket_live" },
];

export function DataSourceStep({
  dataSources,
  selectedSourceId,
  loadState,
  onSourceChange,
  onCreateSource,
}: DataSourceStepProps) {
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState("api_polling");
  const [provider, setProvider] = useState("mock_polling");

  const canCreate = name.trim().length > 0 && provider.trim().length > 0;

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Step 1</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Data source selection</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Select a configured source for freshness checks. Provider keys stay server-side.
          </p>
        </div>
        <Badge value={loadState === "loading" ? "Loading" : "Provider polling available"} tone="info" />
      </div>
      {dataSources.length === 0 ? (
        <OnboardingEmptyState
          title="No data sources returned"
          message="Create a minimal source if the backend allows it, or seed source configuration server-side."
        />
      ) : (
        <div className="grid gap-3">
          {dataSources.map((source) => (
            <label
              key={source.id}
              className={`cursor-pointer rounded-lg border p-4 ${
                selectedSourceId === source.id
                  ? "border-teal-300 bg-teal-50 dark:border-teal-800 dark:bg-teal-950"
                  : "border-[var(--line)] bg-[var(--panel)]"
              }`}
            >
              <input
                type="radio"
                name="data-source"
                className="sr-only"
                checked={selectedSourceId === source.id}
                onChange={() => onSourceChange(source.id)}
              />
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{source.name}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {displaySourceType(source)} · {source.provider}
                  </p>
                </div>
                <Badge value={source.status} tone={toneForQuality(source.status)} />
              </div>
              <p className="mt-3 text-xs text-slate-500">Updated {formatDateTime(source.updated_at)}</p>
            </label>
          ))}
        </div>
      )}
      <div className="mt-6 rounded-lg border border-[var(--line)] p-4">
        <p className="text-sm font-semibold text-[var(--strong)]">Create minimal source config</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Source name"
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
          />
          <select
            value={sourceType}
            onChange={(event) => setSourceType(event.target.value)}
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
          >
            {sourceTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
            placeholder="Provider"
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs leading-5 text-slate-500">
            Secret values are not accepted here. Provider credentials must be configured server-side.
          </p>
          <button
            type="button"
            disabled={!canCreate}
            onClick={() => onCreateSource({ name, sourceType, provider })}
            className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            Create source
          </button>
        </div>
      </div>
    </section>
  );
}

function displaySourceType(source: DataSource): string {
  if (source.source_type === "api_polling") {
    return "provider_polling";
  }
  if (source.source_type === "websocket_live" && source.provider === "mock") {
    return "mock_live";
  }
  return source.source_type;
}
