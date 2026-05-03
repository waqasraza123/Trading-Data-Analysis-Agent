import Link from "next/link";

export type WorkflowTarget = "dashboard" | "brief" | "triage" | "scanner" | "dataOnboarding";

type WorkflowLinksProps = {
  workspaceId?: string | null;
  targets?: WorkflowTarget[];
  className?: string;
};

const workflowTargets: Record<WorkflowTarget, { href: string; label: string }> = {
  dashboard: { href: "/dashboard", label: "Dashboard" },
  brief: { href: "/brief", label: "Brief" },
  triage: { href: "/triage", label: "Triage" },
  scanner: { href: "/scanner", label: "Scanner" },
  dataOnboarding: { href: "/data/onboarding", label: "Data Onboarding" },
};

const linkClassName =
  "rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900";

export function WorkflowLinks({
  workspaceId,
  targets = ["brief", "triage", "scanner", "dataOnboarding"],
  className = "",
}: WorkflowLinksProps) {
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {targets.map((target) => {
        const item = workflowTargets[target];
        return (
          <Link key={target} className={linkClassName} href={workflowHref(target, workspaceId)}>
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}

export function workflowHref(target: WorkflowTarget, workspaceId?: string | null): string {
  const item = workflowTargets[target];
  if (!workspaceId) {
    return item.href;
  }
  return `${item.href}?workspaceId=${workspaceId}`;
}
