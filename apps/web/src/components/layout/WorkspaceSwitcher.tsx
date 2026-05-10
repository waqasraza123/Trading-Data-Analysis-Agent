import { Suspense } from "react";
import { WorkspaceSelector } from "@/components/workspace/WorkspaceSelector";

type WorkspaceSwitcherProps = {
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function WorkspaceSwitcher({ workspaceName, workspaceId }: WorkspaceSwitcherProps) {
  return (
    <Suspense fallback={<div className="muted-surface h-24 rounded-lg" />}>
      <WorkspaceSelector workspaceId={workspaceId} workspaceName={workspaceName} />
    </Suspense>
  );
}
