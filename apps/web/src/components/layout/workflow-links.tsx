import Link from "next/link";

export type WorkflowTarget =
  | "commandCenter"
  | "readiness"
  | "dashboard"
  | "brief"
  | "triage"
  | "scanner"
  | "notifications"
  | "dataOnboarding"
  | "quality"
  | "preferences"
  | "review"
  | "journal";

type WorkflowLinksProps = {
  workspaceId?: string | null;
  targets?: WorkflowTarget[];
  className?: string;
};

export const workflowTargets: Record<WorkflowTarget, { href: string; label: string }> = {
  commandCenter: { href: "/command-center", label: "Command Center" },
  readiness: { href: "/readiness", label: "Readiness" },
  dashboard: { href: "/dashboard", label: "Dashboard" },
  brief: { href: "/brief", label: "Brief" },
  triage: { href: "/triage", label: "Triage" },
  scanner: { href: "/scanner", label: "Scanner" },
  notifications: { href: "/notifications", label: "Notifications" },
  dataOnboarding: { href: "/data/onboarding", label: "Data" },
  quality: { href: "/quality", label: "Quality" },
  preferences: { href: "/preferences/strategy", label: "Preferences" },
  review: { href: "/review/outcomes", label: "Review" },
  journal: { href: "/journal", label: "Journal" },
};

export const primaryWorkflowTargets: WorkflowTarget[] = [
  "commandCenter",
  "readiness",
  "brief",
  "triage",
  "scanner",
  "notifications",
  "dataOnboarding",
  "quality",
  "preferences",
  "review",
  "journal",
];

const linkClassName =
  "rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900";

export function WorkflowLinks({
  workspaceId,
  targets = primaryWorkflowTargets,
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
