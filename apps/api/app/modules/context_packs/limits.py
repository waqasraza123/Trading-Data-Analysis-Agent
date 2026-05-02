from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class ContextPackLimits:
    max_evidence_rows: int
    max_risk_notes: int
    max_audit_events: int
    max_outcomes: int
    max_scenarios: int
    max_action_items: int
    max_news_correlations: int
    max_text_length: int

    @classmethod
    def from_settings(cls, settings: Settings) -> "ContextPackLimits":
        return cls(
            max_evidence_rows=settings.context_pack_max_evidence_rows,
            max_risk_notes=settings.context_pack_max_risk_notes,
            max_audit_events=settings.context_pack_max_audit_events,
            max_outcomes=settings.context_pack_max_outcomes,
            max_scenarios=settings.context_pack_max_scenarios,
            max_action_items=settings.context_pack_max_action_items,
            max_news_correlations=settings.context_pack_max_news_correlations,
            max_text_length=settings.context_pack_max_text_length,
        )

    def with_overrides(
        self,
        max_evidence_rows: int | None = None,
        max_audit_events: int | None = None,
        max_outcomes: int | None = None,
    ) -> "ContextPackLimits":
        return ContextPackLimits(
            max_evidence_rows=max_evidence_rows or self.max_evidence_rows,
            max_risk_notes=self.max_risk_notes,
            max_audit_events=max_audit_events or self.max_audit_events,
            max_outcomes=max_outcomes or self.max_outcomes,
            max_scenarios=self.max_scenarios,
            max_action_items=self.max_action_items,
            max_news_correlations=self.max_news_correlations,
            max_text_length=self.max_text_length,
        )
