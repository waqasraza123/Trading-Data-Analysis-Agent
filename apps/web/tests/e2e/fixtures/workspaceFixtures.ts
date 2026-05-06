import type { Workspace } from "../../../src/lib/api/types";
import type { WorkspaceDefaultContext } from "../../../src/lib/workspace/types";

export const demoWorkspaceId = "11111111-1111-4111-8111-111111111111";
export const demoUserId = "22222222-2222-4222-8222-222222222222";

export const demoWorkspace: Workspace = {
  id: demoWorkspaceId,
  name: "Demo Analysis Workspace",
  created_at: "2026-05-06T08:00:00.000Z",
  updated_at: "2026-05-06T08:00:00.000Z",
};

export const workspaceListWithDemo: Workspace[] = [demoWorkspace];

export const emptyWorkspaceList: Workspace[] = [];

export const selectedWorkspaceDefaultContext: WorkspaceDefaultContext = {
  status: "ready",
  workspace: demoWorkspace,
  user: {
    id: demoUserId,
    role: "analyst",
    name: "Demo Operator",
  },
  available_workspaces: workspaceListWithDemo,
};

export const missingWorkspaceDefaultContext: WorkspaceDefaultContext = {
  status: "missing_workspace",
  workspace: null,
  user: null,
  available_workspaces: emptyWorkspaceList,
};
