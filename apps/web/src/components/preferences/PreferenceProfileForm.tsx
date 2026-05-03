"use client";

import { useRouter } from "next/navigation";
import { FormEvent, ReactNode, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { createPreferenceProfile, updatePreferenceProfile } from "@/lib/api/preferenceProfiles";
import { humanizeLabel } from "@/lib/formatting/labels";
import type {
  PreferenceProfileInput,
  PreferenceProfilesPageData,
} from "@/lib/preferences/types";
import {
  preferenceMarkets,
  preferencePatterns,
  preferenceSessions,
  preferenceTimeframes,
} from "@/lib/preferences/types";
import {
  parseOptionalPositiveInteger,
  parseOptionalScore,
  validatePreferenceProfileInput,
} from "@/lib/preferences/validation";

const notificationCategories = [
  "signal_ready",
  "human_review_requested",
  "outcome_ready",
  "diagnostic_ready",
  "system_health",
];

export function PreferenceProfileForm({ data }: { data: PreferenceProfilesPageData }) {
  const router = useRouter();
  const editing = data.selectedProfile;
  const [name, setName] = useState(editing?.name || "");
  const [description, setDescription] = useState(editing?.description || "");
  const [status, setStatus] = useState(editing?.status || "active");
  const [isDefault, setIsDefault] = useState(editing?.is_default || false);
  const [markets, setMarkets] = useState<string[]>(editing?.market_types_json || []);
  const [symbolIds, setSymbolIds] = useState<string[]>(editing?.symbol_ids_json || []);
  const [excludedSymbolIds, setExcludedSymbolIds] = useState<string[]>(
    editing?.excluded_symbol_ids_json || [],
  );
  const [timeframes, setTimeframes] = useState<string[]>(editing?.timeframes_json || []);
  const [sessions, setSessions] = useState<string[]>(editing?.session_labels_json || []);
  const [patterns, setPatterns] = useState<string[]>(editing?.pattern_types_json || []);
  const [excludedPatterns, setExcludedPatterns] = useState<string[]>(
    editing?.excluded_pattern_types_json || [],
  );
  const [strategyKeys, setStrategyKeys] = useState<string[]>(
    editing?.strategy_profile_keys_json || [],
  );
  const [minimumConfidence, setMinimumConfidence] = useState(editing?.minimum_confidence || "");
  const [minimumSetupQuality, setMinimumSetupQuality] = useState(
    editing?.minimum_setup_quality || "",
  );
  const [maxStaleSeconds, setMaxStaleSeconds] = useState(
    editing?.max_stale_seconds ? String(editing.max_stale_seconds) : "",
  );
  const [requireFreshData, setRequireFreshData] = useState(editing?.require_fresh_data || false);
  const [requireTimeframeAgreement, setRequireTimeframeAgreement] = useState(
    editing?.require_timeframe_agreement || false,
  );
  const [requireAcceptableDataQuality, setRequireAcceptableDataQuality] = useState(
    editing?.require_acceptable_data_quality || false,
  );
  const [includeNewsContext, setIncludeNewsContext] = useState(
    editing?.include_news_context || false,
  );
  const [includeOutcomes, setIncludeOutcomes] = useState(editing?.include_outcomes || false);
  const [notifications, setNotifications] = useState<string[]>(
    readNotificationCategories(editing?.notification_preferences_json),
  );
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    const input: PreferenceProfileInput = {
      workspace_id: data.workspace.id,
      name,
      description: description || undefined,
      is_default: isDefault,
      market_types_json: markets,
      symbol_ids_json: symbolIds,
      excluded_symbol_ids_json: excludedSymbolIds,
      timeframes_json: timeframes,
      session_labels_json: sessions,
      pattern_types_json: patterns,
      excluded_pattern_types_json: excludedPatterns,
      strategy_profile_keys_json: strategyKeys,
      minimum_confidence: parseOptionalScore(minimumConfidence),
      minimum_setup_quality: parseOptionalScore(minimumSetupQuality),
      max_stale_seconds: parseOptionalPositiveInteger(maxStaleSeconds),
      require_fresh_data: requireFreshData,
      require_timeframe_agreement: requireTimeframeAgreement,
      require_acceptable_data_quality: requireAcceptableDataQuality,
      include_news_context: includeNewsContext,
      include_outcomes: includeOutcomes,
      notification_preferences_json: { categories: notifications },
    };
    const validation = validatePreferenceProfileInput(input);
    if (!validation.valid) {
      setMessage(validation.errors.join(" "));
      return;
    }
    setPending(true);
    setMessage(null);
    const result = editing
      ? await updatePreferenceProfile(editing.id, { ...input, status })
      : await createPreferenceProfile(input);
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <Panel
      title={editing ? "Edit preference profile" : "Create preference profile"}
      eyebrow="Personal review scope"
    >
      {message && (
        <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      <form className="space-y-5" onSubmit={submitProfile}>
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput label="Name" maxLength={160} value={name} onChange={setName} />
          <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
            Status
            <select
              className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm"
              value={status}
              onChange={(event) => setStatus(event.target.value as "active" | "paused" | "archived")}
            >
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 md:col-span-2">
            Description
            <textarea
              className="mt-1 min-h-20 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
              maxLength={5000}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <MultiChoice label="Preferred markets" options={preferenceMarkets} selected={markets} onChange={setMarkets} />
          <MultiChoice label="Preferred timeframes" options={preferenceTimeframes} selected={timeframes} onChange={setTimeframes} />
          <MultiChoice label="Preferred sessions" options={preferenceSessions} selected={sessions} onChange={setSessions} />
          <MultiChoice label="Preferred patterns" options={preferencePatterns} selected={patterns} onChange={setPatterns} />
          <MultiChoice label="Avoid patterns" options={preferencePatterns} selected={excludedPatterns} onChange={setExcludedPatterns} />
          <MultiChoice
            label="Strategy profile keys"
            options={data.strategyProfiles.map((profile) => profile.key)}
            selected={strategyKeys}
            onChange={setStrategyKeys}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <MultiSelect
            label="Preferred symbols"
            options={data.symbols.map((symbol) => ({
              label: `${symbol.symbol} · ${symbol.display_name}`,
              value: symbol.id,
            }))}
            selected={symbolIds}
            onChange={setSymbolIds}
          />
          <MultiSelect
            label="Avoid symbols"
            options={data.symbols.map((symbol) => ({
              label: `${symbol.symbol} · ${symbol.display_name}`,
              value: symbol.id,
            }))}
            selected={excludedSymbolIds}
            onChange={setExcludedSymbolIds}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <TextInput label="Minimum confidence" value={minimumConfidence} onChange={setMinimumConfidence} />
          <TextInput label="Minimum setup quality" value={minimumSetupQuality} onChange={setMinimumSetupQuality} />
          <TextInput label="Stale tolerance seconds" value={maxStaleSeconds} onChange={setMaxStaleSeconds} />
        </div>

        <div className="grid gap-3 text-sm font-medium text-slate-600 dark:text-slate-300 md:grid-cols-2">
          <Check checked={isDefault} label="Use as default profile" onChange={setIsDefault} />
          <Check checked={requireFreshData} label="Require fresh data" onChange={setRequireFreshData} />
          <Check checked={requireTimeframeAgreement} label="Require timeframe agreement" onChange={setRequireTimeframeAgreement} />
          <Check checked={requireAcceptableDataQuality} label="Require acceptable data quality" onChange={setRequireAcceptableDataQuality} />
          <Check checked={includeNewsContext} label="Prefer news context when available" onChange={setIncludeNewsContext} />
          <Check checked={includeOutcomes} label="Prefer outcome context when available" onChange={setIncludeOutcomes} />
        </div>

        <MultiChoice
          label="Notification preference categories"
          options={notificationCategories}
          selected={notifications}
          onChange={setNotifications}
        />

        <button
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={pending || !data.workspace}
          type="submit"
        >
          {pending ? "Saving profile" : editing ? "Update profile" : "Create profile"}
        </button>
      </form>
    </Panel>
  );
}

function TextInput({
  label,
  value,
  maxLength,
  onChange,
}: {
  label: string;
  value: string;
  maxLength?: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
      {label}
      <input
        className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm"
        maxLength={maxLength}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function MultiChoice({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: readonly string[];
  selected: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <fieldset>
      <legend className="text-xs font-semibold uppercase text-slate-500">{label}</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => {
          const checked = selected.includes(option);
          return (
            <button
              key={option}
              className={`rounded-md border px-3 py-1.5 text-xs font-medium ${
                checked
                  ? "border-[var(--accent)] bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-100"
                  : "border-[var(--line)] hover:bg-slate-50 dark:hover:bg-slate-900"
              }`}
              onClick={() => onChange(toggleValue(selected, option))}
              type="button"
            >
              {humanizeLabel(option)}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

function MultiSelect({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: Array<{ value: string; label: string }>;
  selected: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
      {label}
      <select
        className="mt-1 h-36 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
        multiple
        value={selected}
        onChange={(event) =>
          onChange(Array.from(event.currentTarget.selectedOptions).map((option) => option.value))
        }
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Check({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: ReactNode;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2">
      <input checked={checked} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
      {label}
    </label>
  );
}

function toggleValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

function readNotificationCategories(value: unknown): string[] {
  if (!isRecord(value)) {
    return [];
  }
  const categories = value.categories;
  if (!Array.isArray(categories)) {
    return [];
  }
  return categories.filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
