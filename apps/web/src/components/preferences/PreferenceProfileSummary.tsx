import { Badge } from "@/components/status/badge";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { humanizeLabel } from "@/lib/formatting/labels";
import type { PreferenceProfilesPageData } from "@/lib/preferences/types";

export function PreferenceProfileSummary({ data }: { data: PreferenceProfilesPageData }) {
  const profile = data.selectedProfile;
  const filters = profile ? countConfiguredFilters(profile) : 0;
  const cards = [
    {
      key: "profiles",
      label: "Profiles",
      value: String(data.profiles.length),
      detail: "Workspace review scopes",
    },
    {
      key: "selected",
      label: "Selected",
      value: profile?.name || "No profile",
      detail: profile?.status ? humanizeLabel(profile.status) : "No active profile",
    },
    {
      key: "configured",
      label: "Configured filters",
      value: String(filters),
      detail: "Review preferences only",
    },
    {
      key: "default",
      label: "Default",
      value: data.profiles.find((item) => item.is_default)?.name || "Not set",
      detail: profile ? humanizeLabel(profile.status) : "Create a profile to start",
      showBadge: true,
    },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-4">
      {cards.map((card, index) => (
        <AnimatedListItem
          as="article"
          key={card.key}
          className={cn(
            "muted-surface rounded-lg p-4",
            motionCardClass,
            motionRevealPresetClass("scale-subtle"),
          )}
          style={motionRevealDensityStyle(index, "compact")}
        >
          <p className="text-xs font-medium uppercase text-slate-500">{card.label}</p>
          <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">
            {card.value}
          </p>
          <p className="mt-1 text-sm text-slate-500">{card.detail}</p>
          {card.showBadge && (
            <div className="mt-2">
              <Badge value={profile?.status || "Unavailable"} tone={profile?.status === "active" ? "good" : "warning"} />
            </div>
          )}
        </AnimatedListItem>
      ))}
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
