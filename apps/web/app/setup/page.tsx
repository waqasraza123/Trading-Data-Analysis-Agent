import { AppShell } from "@/components/layout/AppShell";
import { SetupWizardLayout } from "@/components/setup-wizard/SetupWizardLayout";
import { AnimatedSection } from "@/lib/ui/motion";
import { getSetupWizardInitialData } from "@/lib/api/workspaceSetup";

type SetupPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function SetupPage({ searchParams }: SetupPageProps) {
  const params = await searchParams;
  const data = await getSetupWizardInitialData(params);
  const selectedWorkspace = data.workspaces.find((workspace) => workspace.id === data.selectedWorkspaceId) || null;

  return (
    <AppShell appName={data.appName} workspaceId={selectedWorkspace?.id} workspaceName={selectedWorkspace?.name}>
      <AnimatedSection as="section">
        <SetupWizardLayout initialData={data} />
      </AnimatedSection>
    </AppShell>
  );
}
