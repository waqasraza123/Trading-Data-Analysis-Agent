import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type TabItem = {
  key: string;
  label: string;
  active?: boolean;
  href?: string;
};

type TabsProps = {
  items: TabItem[];
  children?: ReactNode;
  onSelect?: (key: string) => void;
};

export function Tabs({ items, children, onSelect }: TabsProps) {
  return (
    <div className="space-y-4">
      <div className="inline-flex max-w-full flex-wrap gap-1 rounded-2xl border border-[var(--border)] bg-[var(--surface-muted)] p-1">
        {items.map((item) => {
          const className = cn(
            "rounded-xl px-3 py-2 text-sm font-semibold transition",
            item.active
              ? "bg-[var(--surface)] text-[var(--strong)] shadow-soft"
              : "text-[var(--text-muted)] hover:bg-[var(--surface)] hover:text-[var(--strong)]",
          );
          return item.href ? (
            <a key={item.key} className={className} href={item.href}>
              {item.label}
            </a>
          ) : onSelect ? (
            <button key={item.key} className={className} type="button" onClick={() => onSelect(item.key)}>
              {item.label}
            </button>
          ) : (
            <span key={item.key} className={className}>
              {item.label}
            </span>
          );
        })}
      </div>
      {children}
    </div>
  );
}
