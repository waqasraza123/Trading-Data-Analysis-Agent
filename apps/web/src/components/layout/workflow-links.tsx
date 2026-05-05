import Link from "next/link";
import { navigationHref, navigationItems, type NavigationTarget } from "@/lib/ui/navigation";

export type WorkflowTarget = NavigationTarget | "readiness" | "dashboard";

type WorkflowLinksProps = {
  workspaceId?: string | null;
  targets?: WorkflowTarget[];
  className?: string;
};

export const workflowTargets: Record<WorkflowTarget, { href: string; label: string }> = {
  ...(Object.fromEntries(navigationItems.map((item) => [item.key, { href: item.href, label: item.label }])) as Record<NavigationTarget, { href: string; label: string }>),
  readiness: { href: "/readiness", label: "Readiness" },
  dashboard: { href: "/dashboard", label: "Dashboard" },
};

export const primaryWorkflowTargets: WorkflowTarget[] = [
  "commandCenter",
  "brief",
  "dataOnboarding",
  "scanner",
  "triage",
  "quality",
  "notifications",
  "review",
  "journal",
  "preferences",
];

const linkClassName =
  "premium-control rounded-xl px-3 py-2 text-sm font-semibold";

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
  if (target !== "readiness" && target !== "dashboard") {
    return navigationHref(target, workspaceId);
  }
  const item = workflowTargets[target];
  if (!workspaceId) {
    return item.href;
  }
  return `${item.href}?workspaceId=${workspaceId}`;
}
