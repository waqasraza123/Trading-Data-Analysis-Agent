from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.config import AppEnvironment, Settings
from app.core.errors import AppError
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.synthetic_fixtures.generator import SyntheticFixtureGenerator
from app.modules.synthetic_fixtures.schemas import (
    SyntheticFixtureGenerateRequest,
    SyntheticFixtureGenerateResponse,
)

router = APIRouter(prefix="/synthetic-fixtures", tags=["synthetic-fixtures"])


def get_synthetic_fixture_generator(request: Request) -> SyntheticFixtureGenerator:
    settings: Settings = request.app.state.settings
    if settings.app_env == AppEnvironment.PRODUCTION:
        raise AppError(
            403,
            "synthetic_fixtures_disabled_in_production",
            "Synthetic fixture generation API is not available in production",
        )
    if not settings.synthetic_fixtures_api_enabled:
        raise AppError(
            403,
            "synthetic_fixtures_api_disabled",
            "Synthetic fixture generation API is disabled",
        )
    return SyntheticFixtureGenerator(settings.synthetic_fixtures_default_seed)


@router.post(
    "/generate",
    response_model=SyntheticFixtureGenerateResponse,
    dependencies=[Depends(require_permission(Permission.RUNTIME_ADMIN))],
)
async def generate_synthetic_fixture(
    payload: SyntheticFixtureGenerateRequest,
    generator: Annotated[
        SyntheticFixtureGenerator,
        Depends(get_synthetic_fixture_generator),
    ],
) -> SyntheticFixtureGenerateResponse:
    return generator.generate(payload)
