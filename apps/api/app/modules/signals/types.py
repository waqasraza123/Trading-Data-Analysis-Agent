from dataclasses import dataclass
from decimal import Decimal

from app.modules.patterns.models import PatternCandidate
from app.modules.signals.confidence import ConfidenceResult
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.strategy_profiles.models import StrategyProfile


@dataclass(frozen=True)
class CandidateEvaluation:
    profile: StrategyProfile
    candidate: PatternCandidate
    confidence: ConfidenceResult
    ranking_score: Decimal
    classifier_evidence: tuple[dict[str, object], ...]
    risk_notes: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class RejectedCandidate:
    profile_key: str
    pattern_type: str
    reason_code: str
    message: str
    candidate_strength: Decimal


@dataclass(frozen=True)
class ConflictDecision:
    classification_status: SignalClassificationStatus
    bias: SignalBias
    selected_evaluation: CandidateEvaluation | None
    no_signal_reason: str | None
    summary: str
    evidence: tuple[dict[str, object], ...]
    risk_notes: tuple[dict[str, object], ...]
