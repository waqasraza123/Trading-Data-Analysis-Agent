import { AccountSessionControls, RevokeOtherSessionsButton } from "@/components/account/AccountSessionControls";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import {
  ReviewFact,
  ReviewMetricGrid,
  ReviewSurfaceHero,
  ReviewSurfaceMetric,
  ReviewSurfacePanel,
  ReviewTable,
} from "@/components/review-surfaces/ReviewSurface";
import type { AccountFailure, AuthSession, AuthSessionStatus } from "@/lib/api/account";
import { getAccountData } from "@/lib/api/accountServer";
import { formatDateTime, formatRelativeTime, shortIdentifier } from "@/lib/ui/formatters";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";

export default async function AccountPage() {
  const data = await getAccountData();
  const identity = data.authContext?.identity || null;
  const user = identity?.user || null;
  const workspace = identity?.workspace || null;
  const activeSessions = data.sessions.filter((session) => session.status === "active");
  const currentSession = data.sessions.find((session) => session.current) || null;

  return (
    <AppShell appName={data.appName} workspaceId={workspace?.id} workspaceName={workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <ReviewSurfaceHero
            eyebrow="Account"
            title={user?.name || "Session account"}
            description="Current identity, workspace context, and active password sessions."
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <Badge value={identity?.source || "unauthenticated"} tone={identity?.authenticated ? "good" : "warning"} dot />
                <Badge value={workspace?.name || "No workspace"} tone={workspace ? "info" : "neutral"} />
              </div>
            }
          />
        </AnimatedListItem>

        <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "regular")}>
          <ReviewMetricGrid>
            <ReviewSurfaceMetric label="Active sessions" value={activeSessions.length} detail="Non-expired session records" tone={activeSessions.length > 0 ? "good" : "warning"} />
            <ReviewSurfaceMetric label="Current session" value={currentSession ? shortIdentifier(currentSession.id) : "Missing"} detail={currentSession ? formatRelativeTime(currentSession.last_seen_at) : "Bearer cookie was not resolved"} tone={currentSession ? "info" : "warning"} />
            <ReviewSurfaceMetric label="Auth mode" value={data.authContext?.auth_mode || "unknown"} detail={data.authContext?.auth_enabled ? "Backend auth enforced" : "Backend auth not enforced"} />
            <ReviewSurfaceMetric label="Workspace" value={workspace?.name || "None"} detail={workspace?.id ? shortIdentifier(workspace.id) : "No workspace context"} />
          </ReviewMetricGrid>
        </AnimatedListItem>

        <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
          <AccountFailurePanel failures={data.failures} />
        </AnimatedListItem>

        <div className="grid gap-5 xl:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
            <ReviewSurfacePanel title="Identity" eyebrow="Context">
              <div className="grid gap-3">
                <ReviewFact label="Email" value={user?.email || "Not available"} />
                <ReviewFact label="Role" value={user?.role || "Not available"} />
                <ReviewFact label="User ID" value={user?.id ? shortIdentifier(user.id) : "Not available"} />
                <ReviewFact label="Workspace ID" value={workspace?.id ? shortIdentifier(workspace.id) : "Not available"} />
                <ReviewFact label="Permissions" value={identity?.permissions.length || 0} detail={identity?.admin ? "Admin context" : "Role-scoped context"} />
              </div>
            </ReviewSurfacePanel>
          </AnimatedListItem>

          <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
            <ReviewSurfacePanel
              title="Sessions"
              eyebrow="Security"
              action={<RevokeOtherSessionsButton disabled={activeSessions.filter((session) => !session.current).length === 0} />}
            >
              <SessionTable sessions={data.sessions} />
            </ReviewSurfacePanel>
          </AnimatedListItem>
        </div>
      </AnimatedSection>
    </AppShell>
  );
}

function SessionTable({ sessions }: { sessions: AuthSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="muted-surface rounded-lg p-6">
        <p className="text-sm font-medium text-[var(--strong)]">No password sessions found.</p>
      </div>
    );
  }
  return (
    <ReviewTable>
      <thead className="bg-[var(--panel-muted)] text-xs uppercase tracking-wide text-slate-500">
        <tr>
          <th className="px-4 py-3 font-semibold">Session</th>
          <th className="px-4 py-3 font-semibold">Status</th>
          <th className="px-4 py-3 font-semibold">Last seen</th>
          <th className="px-4 py-3 font-semibold">Expires</th>
          <th className="px-4 py-3 font-semibold">Action</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-[var(--line)]">
        {sessions.map((session) => (
          <tr key={session.id}>
            <td className="px-4 py-3">
              <div className="flex flex-col gap-1">
                <span className="font-medium text-[var(--strong)]">{shortIdentifier(session.id)}</span>
                {session.current && <span className="text-xs text-[var(--accent)]">Current browser session</span>}
              </div>
            </td>
            <td className="px-4 py-3">
              <Badge value={session.status} tone={sessionStatusTone(session.status)} dot />
            </td>
            <td className="px-4 py-3 text-sm text-[var(--text-muted)]">
              {session.last_seen_at ? formatDateTime(session.last_seen_at) : "Not recorded"}
            </td>
            <td className="px-4 py-3 text-sm text-[var(--text-muted)]">{formatDateTime(session.expires_at)}</td>
            <td className="px-4 py-3">
              <AccountSessionControls session={session} />
            </td>
          </tr>
        ))}
      </tbody>
    </ReviewTable>
  );
}

function AccountFailurePanel({ failures }: { failures: AccountFailure[] }) {
  const visibleFailures = failures.filter((failure) => !failure.missing);
  if (visibleFailures.length === 0) {
    return null;
  }
  return (
    <div className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] p-4 text-sm">
      <h3 className="font-semibold text-[var(--danger)]">Account data needs review</h3>
      <div className="mt-3 grid gap-2">
        {visibleFailures.map((failure) => (
          <div key={`${failure.label}-${failure.status}`} className="text-[var(--danger)]">
            <span className="font-medium">{failure.label}</span>: {failure.message}
          </div>
        ))}
      </div>
    </div>
  );
}

function sessionStatusTone(status: AuthSessionStatus) {
  if (status === "active") {
    return "good";
  }
  if (status === "expired") {
    return "warning";
  }
  return "neutral";
}
