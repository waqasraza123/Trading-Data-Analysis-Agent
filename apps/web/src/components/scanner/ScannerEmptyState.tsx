type ScannerEmptyStateProps = {
  title: string;
  message: string;
};

export function ScannerEmptyState({ title, message }: ScannerEmptyStateProps) {
  return (
    <div className="muted-surface rounded-lg p-5">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}
