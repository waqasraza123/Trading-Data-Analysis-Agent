type MetricProps = {
  label: string;
  value: string | number;
  detail?: string;
};

export function Metric({ label, value, detail }: MetricProps) {
  return (
    <div className="muted-surface min-w-0 rounded-lg p-4">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-2 truncate text-2xl font-semibold text-[var(--strong)]">{value}</p>
      {detail && <p className="mt-1 text-sm leading-5 text-slate-500">{detail}</p>}
    </div>
  );
}
