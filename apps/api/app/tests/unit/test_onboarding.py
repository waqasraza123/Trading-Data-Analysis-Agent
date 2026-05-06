from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.onboarding import service as onboarding_service_module
from app.modules.onboarding.schemas import (
    OnboardingActionRequest,
    OnboardingActionResponse,
    OnboardingActionType,
    OnboardingDataFreshnessLabel,
    OnboardingNextStepKey,
)
from app.modules.onboarding.service import (
    OnboardingService,
    choose_next_step,
    data_freshness_status,
)


def test_onboarding_next_step_without_workspace() -> None:
    next_step = choose_next_step(
        workspace=False,
        user=False,
        symbols=False,
        data_sources=False,
        data_freshness=OnboardingDataFreshnessLabel.UNKNOWN,
        watchlists=False,
        scan_configs=False,
        readiness_label="unknown",
    )

    assert next_step.key == OnboardingNextStepKey.CREATE_WORKSPACE
    assert next_step.action_type == "create_workspace"


def test_onboarding_data_freshness_no_candles() -> None:
    status = data_freshness_status(
        {
            "status": "failed",
            "summary": "No final candles are available.",
            "metadata": {"final_candle_count": 0},
        }
    )

    assert status.label == OnboardingDataFreshnessLabel.NO_DATA


@pytest.mark.asyncio
async def test_onboarding_unsupported_action_rejected() -> None:
    service = OnboardingService(session=cast(AsyncSession, object()))

    with pytest.raises(AppError) as error:
        await service.run_action(
            OnboardingActionRequest.model_construct(action_type="unsupported", options={})
        )

    assert error.value.code == "unsupported_action"


@pytest.mark.asyncio
async def test_onboarding_seed_symbols_uses_seed_service(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []

    class FakeSession:
        async def commit(self) -> None:
            calls.append("commit")

    class FakeSeedService:
        def __init__(self, session: object) -> None:
            calls.append(session)

        async def seed_symbols(self) -> list[object]:
            return [type("SymbolStub", (), {"id": uuid4()})()]

    async def fake_response_with_status(
        *args: object,
        **kwargs: object,
    ) -> OnboardingActionResponse:
        return OnboardingActionResponse(
            action_type=OnboardingActionType.SEED_SYMBOLS,
            status="completed",
            message="Default symbols seeded.",
            artifact_ids={},
        )

    monkeypatch.setattr(onboarding_service_module, "SeedService", FakeSeedService)
    service = OnboardingService(session=cast(AsyncSession, FakeSession()))
    monkeypatch.setattr(service, "response_with_status", fake_response_with_status)

    response = await service.run_action(
        OnboardingActionRequest(action_type=OnboardingActionType.SEED_SYMBOLS)
    )

    assert response.status == "completed"
    assert calls
    assert "commit" in calls
