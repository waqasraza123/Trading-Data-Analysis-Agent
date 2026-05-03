import { Badge } from "@/components/status/badge";
import { humanizeLabel } from "@/lib/formatting/labels";
import type { PreferenceProfilesPageData } from "@/lib/preferences/types";

export function PreferenceProfileSummary({ data }: { data: PreferenceProfilesPageData }) {
  const profile = data.selectedProfile;
  const filters = profile ? countConfiguredFilters(profile) : 0;

  return (
    <section className="grid gap-4 md:grid-cols-4">
      <div className="muted-surface rounded-lg p-4">
        <p className="text-xs font-medium uppercase text-slate-500">Profiles</p>
        <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{data.profiles.length}</p>
        <p className="mt-1 text-sm text-slate-500">Workspace review scopes</p>
      </div>
      <div className="muted-surface rounded-lg p-4">
        <p className="text-xs font-medium uppercase text-slate-500">Selected</p>
        <p className="mt-2 truncate text-lg font-semibold text-[var(--strong)]">
          {profile?.name || "No profile"}
        </p>
        <div className="mt-2">
          <Badge value={profile?.status || "Unavailable"} tone={profile?.status === "active" ? "good" : "warning"} />
        </div>
      </div>
      <div className="muted-surface rounded-lg p-4">
        <p className="text-xs font-medium uppercase text-slate-500">Configured filters</p>
        <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{filters}</p>
        <p className="mt-1 text-sm text-slate-500">Review preferences only</p>
      </div>
      <div className="muted-surface rounded-lg p-4">
        <p className="text-xs font-medium uppercase text-slate-500">Default</p>
        <p className="mt-2 text-lg font-semibold text-[var(--strong)]">
          {data.profiles.find((item) => item.is_default)?.name || "Not set"}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {profile ? humanizeLabel(profile.status) : "Create a profile to start"}
        </p>
      </div>
    </section>
  );
}

function countConfiguredFilters(profile: NonNullable<PreferenceProfilesPageData["selectedProfile"]>): number {
  return [
    profile.market_types_json,
    profile.symbol_ids_json,
    profile.excluded_symbol_ids_json,
    profile.timeframes_json,
    profile.session_labels_json,
    profile.pattern_types_json,
    profile.excluded_pattern_types_json,
    profile.strategy_profile_keys_json,
  ].filter((items) => items.length > 0).length +
    [
      profile.minimum_confidence,
      profile.minimum_setup_quality,
      profile.max_stale_seconds,
      profile.require_fresh_data,
      profile.require_timeframe_agreement,
      profile.require_acceptable_data_quality,
    ].filter(Boolean).length;
}
