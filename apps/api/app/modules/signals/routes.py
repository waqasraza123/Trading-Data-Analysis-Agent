from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.signals.schemas import SignalClassificationRead
from app.modules.signals.service import SignalClassificationService

router = APIRouter(tags=["signals"])


def get_signal_classification_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SignalClassificationService:
    return SignalClassificationService(session)


@router.get("/signals/{signal_id}", response_model=SignalClassificationRead)
async def get_signal(
    signal_id: UUID,
    service: Annotated[SignalClassificationService, Depends(get_signal_classification_service)],
) -> SignalClassificationRead:
    return await service.get_signal_response(signal_id)
