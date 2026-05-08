import { CommandCenterSkeleton } from "@/components/command-center/CommandCenterSkeleton";
import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";

export default function CommandCenterLoading() {
  return (
    <RouteLoadingShell>
      <CommandCenterSkeleton />
    </RouteLoadingShell>
  );
}
