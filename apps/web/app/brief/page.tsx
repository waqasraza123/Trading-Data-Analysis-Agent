import { BriefNarrative } from "@/components/brief/BriefNarrative";
import { AppShell } from "@/components/layout/AppShell";
import { getWorkspaceBrief } from "@/lib/api/brief";

type BriefPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function BriefPage({ searchParams }: BriefPageProps) {
  const params = await searchParams;
  const brief = await getWorkspaceBrief(params);

  return (
    <AppShell appName={brief.appName} workspaceId={brief.workspace?.id} workspaceName={brief.workspace?.name}>
      <BriefNarrative brief={brief} />
    </AppShell>
  );
}
