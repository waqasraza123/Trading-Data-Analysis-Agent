import { DemoDisabledState } from "@/components/demo/DemoDisabledState";
import { DemoModeHeader } from "@/components/demo/DemoModeHeader";
import { DemoRunButton } from "@/components/demo/DemoRunButton";
import { Panel } from "@/components/layout/panel";
import { AppShell } from "@/components/layout/AppShell";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getPublicEnv } from "@/config/env";
import { getDemoModeStatus } from "@/lib/api/demoMode";
import type { DemoModeStatus } from "@/lib/demo-mode/types";

export default async function DemoPage() {
  const env = getPublicEnv();
  const statusResult = await getDemoModeStatus();
  const status = statusResult.ok ? statusResult.data : null;

  return (
    <AppShell appName={env.appName}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <DemoModeHeader status={status} />
        </AnimatedListItem>
        {!status?.enabled && (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "regular")}>
            <DemoDisabledState status={status} />
          </AnimatedListItem>
        )}
        <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
          <DemoSafetyPanel status={status} />
        </AnimatedListItem>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "regular")}>
          <DemoRunButton enabled={Boolean(status?.enabled)} />
        </AnimatedListItem>
      </AnimatedSection>
    </AppShell>
  );
}

function DemoSafetyPanel({ status }: { status: DemoModeStatus | null }) {
  const notices = status?.safety_notices || [
    "Demo mode uses synthetic deterministic candles only.",
    "Demo mode does not connect to brokers or execute orders.",
    "Demo mode does not auto-trade or provide financial advice.",
  ];
  return (
    <Panel title="Safety boundaries" eyebrow="Demo data">
      <div className="grid gap-3 md:grid-cols-2">
        {notices.map((notice) => (
          <div key={notice} className="muted-surface rounded-lg p-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {notice}
          </div>
        ))}
      </div>
    </Panel>
  );
}
