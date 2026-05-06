import Link from "next/link";
import { withWorkspace } from "@/lib/onboarding/nextStep";

export function OnboardingCompletionPanel({ workspaceId }: { workspaceId?: string | null }) {
  return (
    <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-emerald-950">
      <p className="text-sm font-semibold uppercase tracking-[0.12em]">Command center ready</p>
      <h2 className="mt-2 text-xl font-semibold">Ready for deterministic analysis</h2>
      <p className="mt-2 text-sm leading-6">
        Workspace context, data setup, watchlist, scan config, and readiness status are available.
      </p>
      <Link className="mt-4 inline-flex rounded-md bg-emerald-900 px-4 py-2 text-sm font-semibold text-white" href={withWorkspace("/command-center", workspaceId)}>
        Open command center
      </Link>
    </section>
  );
}
