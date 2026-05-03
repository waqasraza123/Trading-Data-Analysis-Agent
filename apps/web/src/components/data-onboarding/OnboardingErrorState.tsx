import type { OnboardingFailure } from "@/lib/data-onboarding/types";

type OnboardingErrorStateProps = {
  title: string;
  message: string;
  failures?: OnboardingFailure[];
};

export function OnboardingErrorState({ title, message, failures = [] }: OnboardingErrorStateProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6">{message}</p>
      {failures.length > 0 && (
        <div className="mt-4 grid gap-2">
          {failures.map((failure) => (
            <div key={`${failure.label}-${failure.message}`} className="rounded-md border border-red-200 p-3 text-xs dark:border-red-900">
              <p className="font-semibold">{failure.label}</p>
              <p className="mt-1">{failure.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
