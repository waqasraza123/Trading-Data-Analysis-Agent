import { Badge } from "@/components/ui/Badge";
import { workspaceLabel } from "@/lib/ui/labels";

type WorkspaceSwitcherProps = {
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function WorkspaceSwitcher({ workspaceName, workspaceId }: WorkspaceSwitcherProps) {
  const label = workspaceName || workspaceLabel(workspaceId);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">Workspace</p>
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="min-w-0 truncate text-sm font-semibold text-[var(--strong)]">{label}</p>
        <Badge value={workspaceId ? "Selected" : "Global"} tone={workspaceId ? "info" : "neutral"} dot />
      </div>
    </div>
  );
}
