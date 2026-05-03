import Link from "next/link";
import type { ReactNode } from "react";

type AppShellProps = {
  appName: string;
  children: ReactNode;
};

export function AppShell({ appName, children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--line)] bg-[var(--panel)]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <Link href="/dashboard" className="min-w-0">
            <p className="text-xs font-semibold uppercase text-slate-500">Market intelligence</p>
            <h1 className="truncate text-xl font-semibold text-[var(--strong)]">{appName}</h1>
          </Link>
          <nav className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            <Link className="rounded-md px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800" href="/dashboard">
              Dashboard
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
    </div>
  );
}
