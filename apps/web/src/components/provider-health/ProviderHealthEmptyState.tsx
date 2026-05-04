type ProviderHealthEmptyStateProps = {
  title: string;
  message: string;
};

export function ProviderHealthEmptyState({ title, message }: ProviderHealthEmptyStateProps) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--line)] p-5">
      <p className="font-semibold text-[var(--strong)]">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}
