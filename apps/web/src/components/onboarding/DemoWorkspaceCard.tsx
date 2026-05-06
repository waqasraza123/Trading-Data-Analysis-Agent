import type { OnboardingStatusResponse } from "@/lib/onboarding/types";

export function DemoWorkspaceCard({
  status,
  pending,
  onAction,
}: {
  status: OnboardingStatusResponse;
  pending: boolean;
  onAction: () => void;
}) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--strong)]">Demo workspace</p>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Demo mode creates labeled synthetic artifacts for product review. It does not mix demo data with real provider data silently.
          </p>
        </div>
        <span className="rounded-full border border-[var(--line)] px-3 py-1 text-xs font-semibold">
          {status.demo_mode.available ? "Available" : "Unavailable"}
        </span>
      </div>
      <button
        type="button"
        className="mt-4 w-full rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        disabled={!status.demo_mode.available || pending}
        onClick={onAction}
      >
        {pending ? "Creating demo workspace" : status.demo_mode.available ? "Create demo workspace" : "Demo mode unavailable"}
      </button>
    </section>
  );
}
