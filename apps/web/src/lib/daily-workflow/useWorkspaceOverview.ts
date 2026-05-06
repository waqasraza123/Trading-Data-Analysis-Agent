"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getWorkspaceOverview } from "@/lib/api/workspaceOverview";
import type { ApiError, UUID } from "@/lib/api/types";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";
import type { WorkspaceOverviewState } from "./types";

export function useWorkspaceOverview(workspaceId: UUID | null): WorkspaceOverviewState & { refresh: () => Promise<void> } {
  const requestIdRef = useRef(0);
  const [overview, setOverview] = useState<WorkspaceOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    if (!workspaceId) {
      setOverview(null);
      setError(null);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    const result = await getWorkspaceOverview(workspaceId);
    if (requestId !== requestIdRef.current) {
      return;
    }
    if (result.ok) {
      setOverview(result.data);
      setError(null);
      setLastRefreshedAt(new Date().toISOString());
    } else {
      setError(result.error);
    }
    setLoading(false);
  }, [workspaceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { overview, loading, lastRefreshedAt, error, refresh };
}
