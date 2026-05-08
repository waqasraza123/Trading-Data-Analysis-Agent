import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterScanStatus({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Scanner status" eyebrow="Deterministic scans">
          {data.scannerStatus.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.scannerStatus.message}</p>
          ) : (
            <div className="space-y-3">
              {data.scannerStatus.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`block rounded-lg border border-[var(--line)] p-3 transition hover:bg-slate-50 dark:hover:bg-slate-900 ${MOTION_INTERACTIVE_CLASS}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-[var(--strong)]">{item.label}</p>
                    <Badge value={item.status} tone={item.tone} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </Link>
          ))}
        </div>
      )}
      <Link
        href={data.workspace ? `/scanner?workspaceId=${data.workspace.id}` : "/scanner"}
        className={`mt-4 inline-flex rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium transition hover:bg-slate-50 dark:hover:bg-slate-900 ${MOTION_INTERACTIVE_CLASS}`}
      >
        Run deterministic scan
      </Link>
    </Panel>
  );
}
