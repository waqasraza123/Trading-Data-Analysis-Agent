import type { JsonValue } from "@/lib/api/types";

type JsonSectionProps = {
  value: JsonValue | null | undefined;
};

export function JsonSection({ value }: JsonSectionProps) {
  if (value === null || value === undefined) {
    return <p className="text-sm text-slate-500">No structured payload returned.</p>;
  }
  if (typeof value !== "object") {
    return <p className="text-sm text-[var(--strong)]">{String(value)}</p>;
  }
  return (
    <pre className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
