import { CommandCenterCockpit } from "@/components/command-center/CommandCenterCockpit";
import { AppShell } from "@/components/layout/AppShell";
import { getCommandCenterData } from "@/lib/api/commandCenter";

type CommandCenterPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    preferenceProfileId?: string;
    workflowRunId?: string;
    routineRunId?: string;
  }>;
};

export default async function CommandCenterPage({ searchParams }: CommandCenterPageProps) {
  const params = await searchParams;
  const data = await getCommandCenterData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <CommandCenterCockpit data={data} />
    </AppShell>
  );
}
