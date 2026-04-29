from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema, ApiSchema


class EngineVersionRead(ApiReadSchema):
    id: UUID
    engine_name: str
    version: str
    description: str | None
    config_json: dict[str, Any]
    created_at: datetime


class EngineVersionSeedRead(ApiSchema):
    seeded_count: int
    engine_names: list[str]
