type OnboardingEmptyStateProps = {
  title: string;
  message: string;
};

export function OnboardingEmptyState({ title, message }: OnboardingEmptyStateProps) {
  return (
    <div className="muted-surface rounded-lg p-6">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}
