import type { Workspace } from "@/lib/api/types";

type ProviderHealthHeaderProps = {
  workspace: Workspace | null;
  loading: boolean;
  onRefresh: () => void;
};

export function ProviderHealthHeader({ workspace, loading, onRefresh }: ProviderHealthHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">Provider health</p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">
          Real provider freshness and recovery
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
          Check source status, candle freshness, missing candles, recent polling failures, and recovery preparation for {workspace?.name || "the selected workspace"}.
        </p>
      </div>
      <button
        type="button"
        disabled={!workspace || loading}
        onClick={onRefresh}
        className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
      >
        {loading ? "Refreshing" : "Refresh provider health"}
      </button>
    </div>
  );
}
