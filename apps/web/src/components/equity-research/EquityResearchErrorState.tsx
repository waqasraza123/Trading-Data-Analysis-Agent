import type { EquityResearchFailure } from "@/lib/equity-research/types";

export function EquityResearchErrorState({ failures }: { failures: EquityResearchFailure[] }) {
  if (failures.length === 0) {
    return null;
  }
  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
      <h2 className="font-semibold">Some equity research data was unavailable</h2>
      <ul className="mt-2 space-y-1">
        {failures.map((failure) => (
          <li key={`${failure.label}-${failure.status}`}>
            {failure.label}: {failure.message}
          </li>
        ))}
      </ul>
    </section>
  );
}
