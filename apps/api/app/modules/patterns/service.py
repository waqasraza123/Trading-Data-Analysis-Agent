from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.patterns.engine import detect_pattern_candidates
from app.modules.patterns.models import PatternCandidate
from app.modules.patterns.repository import PatternCandidateRepository


class PatternCandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PatternCandidateRepository(session)

    async def create_candidates(
        self,
        analysis_run: AnalysisRun,
        analysis_candles: list[Candle],
        baseline_candles: list[Candle],
        feature_snapshot: FeatureSnapshot,
        indicator_snapshot: IndicatorSnapshot,
    ) -> list[PatternCandidate]:
        drafts = detect_pattern_candidates(
            analysis_candles=analysis_candles,
            baseline_candles=baseline_candles,
            features=feature_snapshot.features_json,
            indicators=indicator_snapshot.indicators_json,
        )
        candidates = [
            PatternCandidate(
                analysis_run_id=analysis_run.id,
                workspace_id=analysis_run.workspace_id,
                symbol_id=analysis_run.symbol_id,
                pattern_type=draft.pattern_type,
                bias=draft.bias,
                strength_score=draft.strength_score,
                is_selected=draft.is_selected,
                evidence_json=draft.serialized_evidence(),
                risk_notes_json=draft.serialized_risk_notes(),
                metrics_json=draft.serialized_metrics(),
            )
            for draft in drafts
        ]
        return await self.repository.replace_for_analysis_run(analysis_run.id, candidates)

    async def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        return await self.repository.list_by_analysis_run_id(analysis_run_id)
