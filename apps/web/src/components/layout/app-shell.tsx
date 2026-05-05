import Link from "next/link";
import type { ReactNode } from "react";
import { PageShell } from "@/components/ui/PageShell";
import { AppNavigation } from "./app-navigation";

type AppShellProps = {
  appName: string;
  children: ReactNode;
};

export function AppShell({ appName, children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="sticky top-0 z-20 border-b border-[var(--line)] bg-[var(--panel)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <Link href="/command-center" className="min-w-0">
            <p className="text-xs font-semibold uppercase text-slate-500">Market intelligence</p>
            <h1 className="truncate text-xl font-semibold text-[var(--strong)]">{appName}</h1>
          </Link>
          <AppNavigation />
        </div>
      </header>
      <PageShell>{children}</PageShell>
    </div>
  );
}
