import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterMissingSections({ overview }: { overview: WorkspaceOverview }) {
  if (overview.missing_sections.length === 0 && overview.warnings.length === 0) {
    return null;
  }
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 dark:border-amber-900 dark:bg-amber-950/35">
      <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">Overview fallback context</p>
      <p className="mt-2 text-sm leading-6 text-amber-800 dark:text-amber-100">
        Some sections are missing or unavailable. The command center keeps using existing page-level composition where possible.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {[...overview.missing_sections, ...overview.warnings].slice(0, 8).map((item) => (
          <span key={item} className="rounded-full border border-amber-300 bg-white/60 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
