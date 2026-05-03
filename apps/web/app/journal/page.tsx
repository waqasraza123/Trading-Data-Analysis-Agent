import { AppShell } from "@/components/layout/app-shell";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { EmptyState } from "@/components/empty-states/empty-state";
import { JournalEntryDetail } from "@/components/journal/JournalEntryDetail";
import { JournalEntryForm } from "@/components/journal/JournalEntryForm";
import { JournalEntryList } from "@/components/journal/JournalEntryList";
import { getJournalData } from "@/lib/api/journal";

type JournalPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function JournalPage({ searchParams }: JournalPageProps) {
  const params = await searchParams;
  const data = await getJournalData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <section className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-500">Journal feedback</p>
            <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Review notes</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              Capture observations, bias, and outcome reflection for deterministic setup review. This page avoids broker execution, account metrics, and financial-advice language.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
              Workspace {data.workspace?.name || "not selected"}
            </div>
            <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "review", "triage", "brief", "preferences"]} />
          </div>
        </section>
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before journal entries can load."
          />
        ) : data.failures.some((failure) => failure.label === "Journal entries" && failure.missing) ? (
          <EmptyState
            title="Journal API unavailable"
            message="The backend did not expose journal entries for this environment. Outcome review can still show available deterministic artifacts."
          />
        ) : (
          <div className="grid gap-5 xl:grid-cols-[minmax(360px,440px)_minmax(0,1fr)]">
            <div className="space-y-5">
              <JournalEntryForm data={data} />
              <JournalEntryList entries={data.entries} workspaceId={data.workspace.id} />
            </div>
            {data.selectedEntry ? (
              <JournalEntryDetail data={data} selectedEntry={data.selectedEntry} />
            ) : (
              <EmptyState
                title="Select or create a note"
                message="Open a journal entry to review it against observed outcomes when linked outcome data is available."
              />
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
