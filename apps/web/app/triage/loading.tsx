import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { TriageSkeleton } from "@/components/triage/TriageSkeleton";

export default function TriageLoading() {
  return (
    <RouteLoadingShell>
      <TriageSkeleton />
    </RouteLoadingShell>
  );
}
