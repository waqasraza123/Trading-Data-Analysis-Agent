"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isActiveNavigationPath, navigationItems } from "@/lib/ui/navigation";

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav className="flex w-full gap-2 overflow-x-auto pb-1 text-sm font-medium text-slate-600 dark:text-slate-300 lg:w-auto lg:flex-wrap lg:justify-end lg:overflow-visible lg:pb-0">
      {navigationItems.map((item) => {
        const active = isActiveNavigationPath(pathname, item.href);
        return (
          <Link
            key={item.key}
            className={`shrink-0 rounded-md px-3 py-2 transition ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
            href={item.href}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
