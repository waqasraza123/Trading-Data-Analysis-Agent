import Link from "next/link";
import { commandCenterGateMessage, withWorkspace } from "@/lib/onboarding/nextStep";
import { onboardingReadinessLabel, onboardingTone } from "@/lib/onboarding/labels";
import type { CommandCenterData } from "@/lib/command-center/types";
import { cn } from "@/lib/ui/cn";
import { motionRevealClass } from "@/lib/ui/motion";

export function CommandCenterReadinessGate({ data }: { data: CommandCenterData }) {
  const status = data.onboardingStatus;
  const gate = commandCenterGateMessage(status);
  const workspaceId = status?.workspace.workspace_id || data.workspace?.id || null;
  if (status?.next_step.key === "open_command_center") {
    return (
      <section className={cn("rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-emerald-950", motionRevealClass())}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Command center ready</p>
            <p className="mt-1 text-sm">Workspace is ready for deterministic analysis.</p>
          </div>
          <Link className="rounded-md border border-emerald-300 px-3 py-2 text-sm font-semibold" href={withWorkspace("/readiness", workspaceId)}>
            Product readiness
          </Link>
        </div>
      </section>
    );
  }
  return (
    <section className={cn("rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950", motionRevealClass())}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold">{gate.title}</p>
            {status && (
              <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${onboardingTone(status.status.readiness_label)}`}>
                {onboardingReadinessLabel(status.status.readiness_label)}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm leading-6">{gate.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-md bg-amber-900 px-3 py-2 text-sm font-semibold text-white" href={withWorkspace("/onboarding", workspaceId)}>
            Open onboarding
          </Link>
          <Link className="rounded-md border border-amber-300 px-3 py-2 text-sm font-semibold" href={gate.href}>
            Review setup context
          </Link>
        </div>
      </div>
    </section>
  );
}
