"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/ui/cn";
import { isActiveNavigationPath, navigationHref, primaryNavigationTargets, navigationItems } from "@/lib/ui/navigation";
import { ApiStatusIndicator } from "./ApiStatusIndicator";

type MobileNavProps = {
  appName: string;
  apiBaseUrl: string;
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function MobileNav({ appName, apiBaseUrl, workspaceName, workspaceId }: MobileNavProps) {
  const pathname = usePathname();
  const items = primaryNavigationTargets
    .map((target) => navigationItems.find((item) => item.key === target))
    .filter((item): item is NonNullable<typeof item> => Boolean(item));

  return (
    <header className="border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_90%,transparent)] px-4 py-3 shadow-soft backdrop-blur-xl">
      <div className="flex items-center justify-between gap-3">
        <Link href={navigationHref("commandCenter", workspaceId)} className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">Market intelligence</p>
          <h1 className="truncate text-base font-semibold text-[var(--strong)]">{appName}</h1>
        </Link>
        <Badge value={workspaceName || (workspaceId ? "Workspace" : "Global")} tone={workspaceId ? "info" : "neutral"} />
      </div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="min-w-0 truncate text-xs text-[var(--text-muted)]">API {apiBaseUrl}</p>
        <ApiStatusIndicator apiBaseUrl={apiBaseUrl} />
      </div>
      <nav className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {items.map((item) => {
          const active = isActiveNavigationPath(pathname, item.href);
          return (
            <Link
              key={item.key}
              className={cn(
                "shrink-0 rounded-full px-3 py-2 text-xs font-semibold transition",
                active ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "bg-[var(--surface-muted)] text-[var(--text-muted)]",
              )}
              href={navigationHref(item.key, workspaceId)}
            >
              {item.shortLabel || item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
