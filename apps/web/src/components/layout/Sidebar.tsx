"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/ui/cn";
import { isActiveNavigationPath, navigationHref, navigationItems, navigationSections } from "@/lib/ui/navigation";
import { AnimatedSection, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealClass, motionRevealDensityStyle } from "@/lib/ui/motion";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

type SidebarProps = {
  appName: string;
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function Sidebar({ appName, workspaceName, workspaceId }: SidebarProps) {
  const pathname = usePathname();

  return (
    <AnimatedSection
      as="aside"
      preset="scale-subtle"
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-3xl border border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_88%,transparent)] p-4 shadow-panel backdrop-blur-xl",
      )}
    >
      <Link href={navigationHref("commandCenter", workspaceId)} className={`group flex items-center gap-3 rounded-2xl p-2 transition hover:bg-[var(--surface-muted)] ${MOTION_INTERACTIVE_CLASS}`}>
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--accent)_0%,var(--info)_100%)] text-sm font-black text-white shadow-glow">
          TI
        </span>
        <span className="min-w-0">
          <span className="block text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">Market intelligence</span>
          <span className="block truncate text-base font-semibold text-[var(--strong)]">{appName}</span>
        </span>
      </Link>
      <div className="mt-4">
        <WorkspaceSwitcher workspaceId={workspaceId} workspaceName={workspaceName} />
      </div>
      <nav className="mt-5 flex-1 overflow-y-auto pr-1">
        <div className="space-y-5">
          {navigationSections.map((section) => {
            const items = navigationItems.filter((item) => item.section === section);
            return (
              <div key={section}>
                <p className="px-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-muted)]">{section}</p>
                <div className="mt-2 space-y-1">
                  {items.map((item, index) => {
                    const active = isActiveNavigationPath(pathname, item.href);
                    return (
                    <Link
                        key={item.key}
                        className={cn(
                          "group flex items-center justify-between gap-3 rounded-2xl px-3 py-2.5 text-sm font-semibold transition",
                          motionCardClass,
                          motionRevealClass(),
                          MOTION_INTERACTIVE_CLASS,
                          active
                            ? "bg-[var(--accent-soft)] text-[var(--accent-strong)] shadow-[inset_0_1px_0_rgba(255,255,255,0.36)]"
                            : "text-[var(--text-muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--strong)]",
                        )}
                        style={motionRevealDensityStyle(index, "compact")}
                        href={navigationHref(item.key, workspaceId)}
                      >
                        <span className="min-w-0 truncate">{item.label}</span>
                        {active && <Badge value="Active" tone="good" className="px-2 py-0.5" />}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </nav>
    </AnimatedSection>
  );
}
