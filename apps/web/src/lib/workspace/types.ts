import type { UUID, Workspace } from "@/lib/api/types";

export type WorkspaceSelection = {
  workspaceId: UUID | null;
  workspaceName: string | null;
};

export type WorkspaceDefaultContext = {
  status: "ready" | "missing_workspace" | string;
  workspace: Workspace | null;
  user: {
    id: UUID;
    role: string;
    name: string | null;
  } | null;
  available_workspaces: Workspace[];
};
