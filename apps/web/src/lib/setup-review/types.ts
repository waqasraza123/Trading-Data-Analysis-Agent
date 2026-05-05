import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import type { StatusTone } from "@/lib/ui/statusStyles";

export type SetupReviewModel = SetupDetailViewModel & {
  summaryMetrics: SetupReviewMetric[];
  sectionCounts: {
    supportingEvidence: number;
    conflictingEvidence: number;
    confidenceComponents: number;
    riskNotes: number;
    waitConditions: number;
    avoidReasons: number;
    outcomes: number;
    historicalCases: number;
    auditEvents: number;
    journalEntries: number;
  };
};

export type SetupReviewMetric = {
  label: string;
  value: string;
  detail?: string;
  tone?: StatusTone;
};
