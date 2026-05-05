import type { ReactNode } from "react";

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
      <div className="flex flex-wrap gap-2">
        {items.map((item) => {
          const className = `rounded-md border px-3 py-2 text-sm font-semibold ${
            item.active
              ? "border-teal-300 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-100"
              : "border-[var(--line)] bg-[var(--panel)] text-slate-600 dark:text-slate-300"
          }`;
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
