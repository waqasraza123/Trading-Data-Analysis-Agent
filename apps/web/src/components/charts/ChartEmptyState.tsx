export function ChartEmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex min-h-56 items-center justify-center rounded-lg border border-dashed border-[var(--line)] bg-[var(--panel-muted)] p-6 text-center">
      <div>
        <p className="text-sm font-semibold text-[var(--strong)]">{title}</p>
        <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">{message}</p>
      </div>
    </div>
  );
}
