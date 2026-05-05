import type { SetupChartFailure } from "@/lib/api/setupChart";

export function ChartErrorState({ failures }: { failures: SetupChartFailure[] }) {
  if (failures.length === 0) {
    return null;
  }
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
      <p className="font-semibold">Chart context warnings</p>
      <ul className="mt-2 space-y-1">
        {failures.slice(0, 4).map((failure) => (
          <li key={`${failure.label}-${failure.status}`}>
            {failure.label}: {failure.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
