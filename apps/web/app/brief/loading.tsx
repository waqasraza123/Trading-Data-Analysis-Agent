import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { BriefSkeleton } from "@/components/brief/BriefSkeleton";

export default function BriefLoading() {
  return (
    <RouteLoadingShell>
      <BriefSkeleton />
    </RouteLoadingShell>
  );
}
