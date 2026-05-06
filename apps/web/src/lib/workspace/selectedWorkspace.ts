import type { Workspace } from "@/lib/api/types";

export const selectedWorkspaceStorageKey = "trading-intelligence:selected-workspace-id";

export function readSelectedWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(selectedWorkspaceStorageKey);
}

export function writeSelectedWorkspaceId(workspaceId: string | null): void {
  if (typeof window === "undefined") return;
  if (workspaceId) {
    window.localStorage.setItem(selectedWorkspaceStorageKey, workspaceId);
  } else {
    window.localStorage.removeItem(selectedWorkspaceStorageKey);
  }
}

export function resolveSelectedWorkspace(
  workspaces: Workspace[],
  explicitWorkspaceId?: string | null,
  storedWorkspaceId?: string | null,
): Workspace | null {
  return (
    workspaces.find((workspace) => workspace.id === explicitWorkspaceId) ||
    workspaces.find((workspace) => workspace.id === storedWorkspaceId) ||
    workspaces[0] ||
    null
  );
}

export function workspaceScopedHref(pathname: string, workspaceId: string | null): string {
  const url = new URL(pathname, "http://local");
  if (workspaceId) {
    url.searchParams.set("workspaceId", workspaceId);
  } else {
    url.searchParams.delete("workspaceId");
  }
  return `${url.pathname}${url.search}`;
}
