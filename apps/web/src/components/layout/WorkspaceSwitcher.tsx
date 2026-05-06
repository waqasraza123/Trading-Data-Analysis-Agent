import { WorkspaceSelector } from "@/components/workspace/WorkspaceSelector";

type WorkspaceSwitcherProps = {
  workspaceName?: string | null;
  workspaceId?: string | null;
};

export function WorkspaceSwitcher({ workspaceName, workspaceId }: WorkspaceSwitcherProps) {
  return <WorkspaceSelector workspaceId={workspaceId} workspaceName={workspaceName} />;
}
