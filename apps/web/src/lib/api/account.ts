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
export type AuthActivityStatus = "success" | "failure";
export type AuthActivityEventType =
  | "register"
  | "login"
  | "logout"
  | "password_change"
  | "session_revoke"
  | "session_revoke_other"
  | "api_key_create"
  | "api_key_revoke";

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

export type AuthPasswordChange = {
  changed: boolean;
  revoked_session_count: number;
};

export type AuthActivityEvent = {
  id: UUID;
  user_id: UUID | null;
  workspace_id: UUID | null;
  event_type: AuthActivityEventType;
  status: AuthActivityStatus;
  identity_source: string | null;
  request_id: string | null;
  error_code: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type AccountFailure = ApiError & {
  label: string;
};

export type AccountData = {
  appName: string;
  authContext: AuthContext | null;
  sessions: AuthSession[];
  activity: AuthActivityEvent[];
  failures: AccountFailure[];
  lastLoadedAt: string;
};

export function getAuthContext(): Promise<ApiResult<AuthContext>> {
  return apiGet<AuthContext>("/auth/context", { optional: true });
}

export function listAuthSessions(): Promise<ApiResult<AuthSession[]>> {
  return apiGet<AuthSession[]>("/auth/sessions", { optional: true });
}

export function listAuthActivity(): Promise<ApiResult<AuthActivityEvent[]>> {
  return apiGet<AuthActivityEvent[]>("/auth/activity", { optional: true });
}

export function revokeAuthSession(sessionId: UUID): Promise<ApiResult<AuthSession>> {
  return apiPost<AuthSession>(`/auth/sessions/${sessionId}/revoke`, undefined, { optional: true });
}

export function revokeOtherAuthSessions(): Promise<ApiResult<AuthSessionBulkRevoke>> {
  return apiPost<AuthSessionBulkRevoke>("/auth/sessions/revoke-other", undefined, {
    optional: true,
  });
}

export function changePassword(payload: {
  currentPassword: string;
  newPassword: string;
  revokeOtherSessions: boolean;
}): Promise<ApiResult<AuthPasswordChange>> {
  return apiPost<AuthPasswordChange>(
    "/auth/password/change",
    {
      currentPassword: payload.currentPassword,
      newPassword: payload.newPassword,
      revokeOtherSessions: payload.revokeOtherSessions,
    },
    { optional: true },
  );
}
