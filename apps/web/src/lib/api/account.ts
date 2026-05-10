import { apiGet, apiPost } from "./client";
import type { ApiError, ApiResult, UUID } from "./types";

export type AccountIdentity = {
  authenticated: boolean;
  source: string | null;
  provider: string | null;
  provider_subject: string | null;
  user: {
    id: UUID;
    workspace_id: UUID;
    email: string;
    name: string;
    role: string;
  } | null;
  workspace: {
    id: UUID;
    name: string;
  } | null;
  permissions: string[];
  scopes: string[];
  admin: boolean;
};

export type AuthContext = {
  auth_mode: string;
  auth_enabled: boolean;
  jwt_enabled: boolean;
  api_keys_enabled: boolean;
  api_key_header_name: string;
  user_context_header_name: string;
  workspace_context_header_name: string;
  identity: AccountIdentity;
};

export type AuthSessionStatus = "active" | "revoked" | "expired";

export type AuthSession = {
  id: UUID;
  user_id: UUID;
  workspace_id: UUID;
  status: AuthSessionStatus;
  expires_at: string;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
  current: boolean;
};

export type AuthSessionBulkRevoke = {
  revoked_count: number;
};

export type AccountFailure = ApiError & {
  label: string;
};

export type AccountData = {
  appName: string;
  authContext: AuthContext | null;
  sessions: AuthSession[];
  failures: AccountFailure[];
  lastLoadedAt: string;
};

export function getAuthContext(): Promise<ApiResult<AuthContext>> {
  return apiGet<AuthContext>("/auth/context", { optional: true });
}

export function listAuthSessions(): Promise<ApiResult<AuthSession[]>> {
  return apiGet<AuthSession[]>("/auth/sessions", { optional: true });
}

export function revokeAuthSession(sessionId: UUID): Promise<ApiResult<AuthSession>> {
  return apiPost<AuthSession>(`/auth/sessions/${sessionId}/revoke`, undefined, { optional: true });
}

export function revokeOtherAuthSessions(): Promise<ApiResult<AuthSessionBulkRevoke>> {
  return apiPost<AuthSessionBulkRevoke>("/auth/sessions/revoke-other", undefined, {
    optional: true,
  });
}
