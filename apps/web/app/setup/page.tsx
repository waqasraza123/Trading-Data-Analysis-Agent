import { AppShell } from "@/components/layout/app-shell";
import { SetupWizardLayout } from "@/components/setup-wizard/SetupWizardLayout";
import { getSetupWizardInitialData } from "@/lib/api/workspaceSetup";

type SetupPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function SetupPage({ searchParams }: SetupPageProps) {
  const params = await searchParams;
  const data = await getSetupWizardInitialData(params);

  return (
    <AppShell appName={data.appName}>
      <SetupWizardLayout initialData={data} />
    </AppShell>
  );
}
