"use client";

import { useEffect, useState } from "react";
import { StatusPill } from "@/components/ui/StatusPill";
import { getPublicEnv } from "@/config/env";
import { authHeaders } from "@/lib/api/client";
import type { StatusTone } from "@/lib/ui/statusStyles";

type ApiStatusIndicatorProps = {
  apiBaseUrl: string;
};

type ApiStatusState = {
  label: string;
  tone: StatusTone;
};

export function ApiStatusIndicator({ apiBaseUrl }: ApiStatusIndicatorProps) {
  const [state, setState] = useState<ApiStatusState>({ label: "Checking", tone: "info" });

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 3500);
    let active = true;

    fetch(`${apiBaseUrl}/health`, {
      cache: "no-store",
      headers: authHeaders(getPublicEnv()),
      signal: controller.signal,
    })
      .then((response) => {
        if (active) {
          setState(response.ok ? { label: "Online", tone: "good" } : { label: "Degraded", tone: "warning" });
        }
      })
      .catch(() => {
        if (active) {
          setState({ label: "Offline", tone: "warning" });
        }
      })
      .finally(() => window.clearTimeout(timeout));

    return () => {
      active = false;
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [apiBaseUrl]);

  return <StatusPill label="API" value={state.label} tone={state.tone} />;
}
