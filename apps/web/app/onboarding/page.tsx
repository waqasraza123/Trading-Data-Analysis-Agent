import { AppShell } from "@/components/layout/AppShell";
import { OnboardingShell } from "@/components/onboarding/OnboardingShell";
import { AnimatedSection } from "@/lib/ui/motion";
import { getOnboardingPageData } from "@/lib/api/onboarding";

type OnboardingPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    userId?: string;
  }>;
};

export default async function OnboardingPage({ searchParams }: OnboardingPageProps) {
  const params = await searchParams;
  const data = await getOnboardingPageData(params);

  return (
    <AppShell
      appName={data.appName}
      workspaceId={data.status?.workspace.workspace_id || data.selectedWorkspaceId}
      workspaceName={data.status?.workspace.name}
    >
      <AnimatedSection as="section">
        <OnboardingShell initialData={data} />
      </AnimatedSection>
    </AppShell>
  );
}
