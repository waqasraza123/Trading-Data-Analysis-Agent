import { Badge } from "@/components/ui/Badge";
import { ApiStatusIndicator } from "./ApiStatusIndicator";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

type TopbarProps = {
  apiBaseUrl: string;
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function Topbar({ apiBaseUrl, workspaceName, workspaceId }: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 hidden border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_72%,transparent)] px-8 py-4 backdrop-blur-xl lg:block">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">Trading intelligence cockpit</p>
          <h1 className="mt-1 truncate text-lg font-semibold text-[var(--strong)]">Daily read-only workspace</h1>
        </div>
        <div className="flex items-center gap-3">
          <ApiStatusIndicator apiBaseUrl={apiBaseUrl} />
          <Badge value={apiBaseUrl} tone="neutral" className="max-w-72" />
          <div className="w-72">
            <WorkspaceSwitcher workspaceId={workspaceId} workspaceName={workspaceName} />
          </div>
        </div>
      </div>
    </header>
  );
}
