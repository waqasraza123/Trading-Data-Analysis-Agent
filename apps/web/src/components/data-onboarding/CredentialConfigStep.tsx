import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import type {
  DataSource,
  ProviderConnectionTest,
  ProviderCredentialRef,
} from "@/lib/data-onboarding/types";

type CredentialConfigStepProps = {
  dataSources: DataSource[];
  providerCredentialRefs: ProviderCredentialRef[];
  credentialTests: Record<string, ProviderConnectionTest>;
  credentialTestState: Record<string, string>;
  selectedSourceId: string | null;
  onTestSourceCredential: (source: DataSource) => void;
};

export function CredentialConfigStep({
  dataSources,
  providerCredentialRefs,
  credentialTests,
  credentialTestState,
  selectedSourceId,
  onTestSourceCredential,
}: CredentialConfigStepProps) {
  const selectedSource = dataSources.find((source) => source.id === selectedSourceId) || null;
  const selectedCredential = selectedSource
    ? credentialRefForSource(selectedSource, providerCredentialRefs)
    : null;

  return (
    <section className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Credentials/config
          </p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">
            Server-side provider configuration
          </h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Review whether provider references are configured. Secret values are never displayed or
            entered in this workflow.
          </p>
        </div>
        <Badge
          value={selectedCredential?.secret_ref_configured ? "Source configured" : "Credential review needed"}
          tone={selectedCredential?.secret_ref_configured ? "good" : "warning"}
        />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="overflow-x-auto rounded-lg border border-[var(--line)]">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-[var(--panel-muted)] text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Source</th>
                <th className="px-4 py-3 font-semibold">Provider</th>
                <th className="px-4 py-3 font-semibold">Credential status</th>
                <th className="px-4 py-3 font-semibold">Test status</th>
                <th className="px-4 py-3 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)]">
              {dataSources.map((source) => {
                const credential = credentialRefForSource(source, providerCredentialRefs);
                const latestTest = credentialTests[source.id] || null;
                const testState = credentialTestState[source.id] || "idle";
                const status = latestTest?.status || credential?.last_test_status || credential?.status || "missing";
                return (
                  <tr key={source.id} className={source.id === selectedSourceId ? "bg-teal-50/70 dark:bg-teal-950/40" : ""}>
                    <td className="px-4 py-3">
                      <p className="font-semibold text-[var(--strong)]">{source.name}</p>
                      <p className="mt-1 text-xs text-slate-500">{source.source_type}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{source.provider}</td>
                    <td className="px-4 py-3">
                      <Badge value={credential?.secret_ref_configured ? "configured" : "missing"} tone={credential?.secret_ref_configured ? "good" : "warning"} />
                      <p className="mt-1 text-xs text-slate-500">
                        {credential ? credential.name : "No linked secret reference"}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge value={status} tone={statusTone(status)} />
                      <p className="mt-1 text-xs text-slate-500">
                        {formatDateTime(latestTest?.created_at || credential?.last_tested_at)}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        disabled={testState === "loading"}
                        onClick={() => onTestSourceCredential(source)}
                        className="rounded-md border border-[var(--line)] px-3 py-2 text-xs font-semibold text-[var(--strong)] disabled:opacity-40"
                      >
                        {testState === "loading" ? "Testing" : "Test config"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <aside className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
          <p className="text-sm font-semibold text-[var(--strong)]">Configuration guidance</p>
          <div className="mt-3 grid gap-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            <p>Use provider credential references for server-side secrets.</p>
            <p>Use configuration-only tests for public or mock providers.</p>
            <p>Return here after backend configuration changes to refresh source status.</p>
          </div>
        </aside>
      </div>
    </section>
  );
}

function credentialRefForSource(
  source: DataSource,
  credentials: ProviderCredentialRef[],
): ProviderCredentialRef | null {
  if (source.credential_ref_id) {
    return credentials.find((credential) => credential.id === source.credential_ref_id) || null;
  }
  const provider = credentialProviderForSource(source);
  return (
    credentials.find(
      (credential) =>
        credential.provider === provider &&
        credential.workspace_id === source.workspace_id &&
        credential.status !== "revoked",
    ) || null
  );
}

function credentialProviderForSource(source: DataSource): string {
  if (source.provider === "binance_public_rest") {
    return "binance";
  }
  if (source.provider === "generic_ohlc_http") {
    return "generic_http";
  }
  if (source.provider === "mock_polling" || source.provider === "mock_live") {
    return "mock";
  }
  return source.provider;
}

function statusTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (normalized === "configured" || normalized === "active" || normalized === "passed") {
    return "good";
  }
  if (normalized === "missing" || normalized === "paused" || normalized === "provider_not_configured") {
    return "warning";
  }
  if (normalized === "failed" || normalized === "revoked" || normalized === "test_failed") {
    return "danger";
  }
  return "neutral";
}
