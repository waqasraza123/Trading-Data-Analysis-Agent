import type { ApiError } from "@/lib/api/types";

type ProviderHealthErrorStateProps = {
  error: ApiError;
};

export function ProviderHealthErrorState({ error }: ProviderHealthErrorStateProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
      <p className="font-semibold">Provider health unavailable</p>
      <p className="mt-1">{error.missing ? "Provider health endpoints are not deployed." : error.message}</p>
    </div>
  );
}
