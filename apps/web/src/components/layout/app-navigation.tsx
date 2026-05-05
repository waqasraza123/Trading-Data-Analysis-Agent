"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/ui/cn";
import { isActiveNavigationPath, navigationHref, navigationItems } from "@/lib/ui/navigation";

type AppNavigationProps = {
  workspaceId?: string | null;
};

export function AppNavigation({ workspaceId }: AppNavigationProps = {}) {
  const pathname = usePathname();

  return (
    <nav className="flex w-full gap-2 overflow-x-auto pb-1 text-sm font-semibold text-[var(--text-muted)] lg:w-auto lg:flex-wrap lg:justify-end lg:overflow-visible lg:pb-0">
      {navigationItems.map((item) => {
        const active = isActiveNavigationPath(pathname, item.href);
        return (
          <Link
            key={item.key}
            className={cn(
              "shrink-0 rounded-full px-3 py-2 transition",
              active ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "hover:bg-[var(--surface-muted)] hover:text-[var(--strong)]",
            )}
            href={navigationHref(item.key, workspaceId)}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
