"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import {
  archivePreferenceProfile,
  setDefaultPreferenceProfile,
} from "@/lib/api/preferenceProfiles";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { humanizeLabel } from "@/lib/formatting/labels";
import type { PreferenceProfilesPageData } from "@/lib/preferences/types";

export function PreferenceProfileList({ data }: { data: PreferenceProfilesPageData }) {
  const router = useRouter();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function archiveProfile(profileId: string) {
    setPendingAction(`archive-${profileId}`);
    setMessage(null);
    const result = await archivePreferenceProfile(profileId);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  async function setDefaultProfile(profileId: string) {
    setPendingAction(`default-${profileId}`);
    setMessage(null);
    const result = await setDefaultPreferenceProfile(profileId);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <Panel title="Preference profiles" eyebrow="Review filters">
      {message && (
        <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      {data.profiles.length === 0 ? (
        <p className="muted-surface rounded-lg p-5 text-sm text-slate-500">
          No preference profiles have been created for this workspace.
        </p>
      ) : (
        <div className="space-y-3">
          {data.profiles.map((profile, index) => (
            <AnimatedListItem
              as="article"
              key={profile.id}
              className={cn(
                "muted-surface rounded-lg p-4",
                motionCardClass,
                motionRevealPresetClass("scale-subtle"),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-[var(--strong)]">{profile.name}</h3>
                    {profile.is_default && <Badge value="Default" tone="good" />}
                    <Badge value={profile.status} tone={profile.status === "active" ? "good" : "warning"} />
                  </div>
                  {profile.description && (
                    <p className="mt-1 text-sm leading-6 text-slate-500">{profile.description}</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-900"
                    href={`/preferences/strategy?workspaceId=${profile.workspace_id}&profileId=${profile.id}`}
                  >
                    Edit
                  </Link>
                  {!profile.is_default && profile.status === "active" && (
                    <button
                      className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-60 dark:hover:bg-slate-900"
                      disabled={pendingAction === `default-${profile.id}`}
                      onClick={() => setDefaultProfile(profile.id)}
                      type="button"
                    >
                      Set default
                    </button>
                  )}
                  {profile.status !== "archived" && (
                    <button
                      className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-60 dark:hover:bg-slate-900"
                      disabled={pendingAction === `archive-${profile.id}`}
                      onClick={() => archiveProfile(profile.id)}
                      type="button"
                    >
                      Archive
                    </button>
                  )}
                </div>
              </div>
              <dl className="mt-4 grid gap-3 text-sm md:grid-cols-3">
                <ProfileStat label="Markets" value={profile.market_types_json.map(humanizeLabel).join(", ")} />
                <ProfileStat label="Timeframes" value={profile.timeframes_json.join(", ")} />
                <ProfileStat label="Sessions" value={profile.session_labels_json.map(humanizeLabel).join(", ")} />
                <ProfileStat label="Patterns" value={profile.pattern_types_json.map(humanizeLabel).join(", ")} />
                <ProfileStat label="Avoid patterns" value={profile.excluded_pattern_types_json.map(humanizeLabel).join(", ")} />
                <ProfileStat label="Minimum confidence" value={profile.minimum_confidence || "Not set"} />
              </dl>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}

function ProfileStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 text-slate-700 dark:text-slate-200">{value || "Any"}</dd>
    </div>
  );
}
