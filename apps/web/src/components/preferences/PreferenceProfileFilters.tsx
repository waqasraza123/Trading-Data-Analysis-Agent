import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import type { PreferenceProfilesPageData } from "@/lib/preferences/types";

export function PreferenceProfileFilters({ data }: { data: PreferenceProfilesPageData }) {
  return (
    <Panel title="Preference scope" eyebrow="Workspace and selected profile">
      <form action="/preferences/strategy" className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Workspace
          <select
            className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm"
            defaultValue={data.workspace?.id || ""}
            name="workspaceId"
          >
            {data.workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Profile
          <select
            className="mt-1 h-10 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 text-sm"
            defaultValue={data.selectedProfile?.id || ""}
            name="profileId"
          >
            <option value="">Default or first profile</option>
            {data.profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end gap-2">
          <button
            className="h-10 rounded-md bg-[var(--accent)] px-4 text-sm font-semibold text-white"
            type="submit"
          >
            Apply
          </button>
          <Link
            className="flex h-10 items-center rounded-md border border-[var(--line)] px-4 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900"
            href="/preferences/strategy"
          >
            Reset
          </Link>
        </div>
      </form>
    </Panel>
  );
}
