import Link from "next/link";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { DemoModeArtifactLink } from "@/lib/demo-mode/types";

export function DemoResultLinks({ links }: { links: DemoModeArtifactLink[] }) {
  if (links.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((link, index) => (
        <AnimatedListItem
          as="article"
          key={`${link.artifact_type}-${link.artifact_id || link.href}`}
          style={motionRevealDensityStyle(index, "compact")}
          className={motionRevealPresetClass("scale-subtle")}
        >
          <Link
            href={link.href}
            className={cn(
              "rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800",
              motionCardClass,
            )}
          >
            {link.label}
          </Link>
        </AnimatedListItem>
      ))}
    </div>
  );
}
