import Link from "next/link";
import type { DemoModeArtifactLink } from "@/lib/demo-mode/types";

export function DemoResultLinks({ links }: { links: DemoModeArtifactLink[] }) {
  if (links.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((link) => (
        <Link
          key={`${link.artifact_type}-${link.artifact_id || link.href}`}
          className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800"
          href={link.href}
        >
          {link.label}
        </Link>
      ))}
    </div>
  );
}
