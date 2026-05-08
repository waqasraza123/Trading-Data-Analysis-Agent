import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import { formatDateTime } from "@/lib/formatting/dates";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle } from "@/lib/ui/motion";

export function FollowUpPanel({ data }: { data: DashboardData }) {
  return (
    <Panel title="Backend Follow-Up" eyebrow="Pending action items">
      {data.dueActionItems.length === 0 ? (
        <EmptyState title="No pending action items" message="The backend did not return due follow-up work for this workspace." />
      ) : (
        <div className="space-y-3">
          {data.dueActionItems.slice(0, 8).map((item, index) => (
            <AnimatedListItem
              as="article"
              key={item.id}
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-semibold text-[var(--strong)]">{item.title || item.action_type}</h3>
                <Badge value={item.status} tone={toneForQuality(item.status)} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.description}</p>
              <p className="mt-2 text-xs text-slate-500">Due {formatDateTime(item.due_at)}</p>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}
