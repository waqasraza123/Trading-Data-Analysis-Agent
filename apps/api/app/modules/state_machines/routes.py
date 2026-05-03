from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.state_machines.schemas import (
    StateMachineDefinitionRead,
    StateMachineSeedRead,
    StateTransitionValidationRead,
    StateTransitionValidationRequest,
)
from app.modules.state_machines.service import StateMachineService

router = APIRouter(prefix="/state-machines", tags=["state-machines"])


def get_state_machine_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> StateMachineService:
    return StateMachineService(session)


@router.get("", response_model=list[StateMachineDefinitionRead])
async def list_state_machines(
    service: Annotated[StateMachineService, Depends(get_state_machine_service)],
    object_type: Annotated[str | None, Query(alias="objectType")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[StateMachineDefinitionRead]:
    definitions = await service.list_state_machines(
        object_type=object_type,
        status=status_filter,
    )
    return [StateMachineDefinitionRead.model_validate(definition) for definition in definitions]


@router.get("/{key}", response_model=StateMachineDefinitionRead)
async def get_state_machine(
    key: str,
    service: Annotated[StateMachineService, Depends(get_state_machine_service)],
    version: str | None = None,
) -> StateMachineDefinitionRead:
    definition = await service.get_state_machine_or_error(key, version=version)
    return StateMachineDefinitionRead.model_validate(definition)


@router.post(
    "/seed-default",
    response_model=StateMachineSeedRead,
    status_code=status.HTTP_200_OK,
)
async def seed_default_state_machines(
    service: Annotated[StateMachineService, Depends(get_state_machine_service)],
) -> StateMachineSeedRead:
    result = await service.seed_default_state_machines()
    await service.session.commit()
    return StateMachineSeedRead(
        seeded_count=result.seeded_count,
        updated_count=result.updated_count,
        keys=result.keys,
    )


@router.post("/validate-transition", response_model=StateTransitionValidationRead)
async def validate_transition(
    payload: StateTransitionValidationRequest,
    service: Annotated[StateMachineService, Depends(get_state_machine_service)],
) -> StateTransitionValidationRead:
    result = await service.validate_and_record_transition(
        object_type=payload.object_type,
        from_state=payload.from_state,
        to_state=payload.to_state,
        workspace_id=payload.workspace_id,
        object_id=payload.object_id,
        state_machine_key=payload.state_machine_key,
        state_machine_version=payload.state_machine_version,
        record_validation=payload.record_validation,
    )
    if payload.record_validation:
        await service.session.commit()
    return StateTransitionValidationRead(
        state_machine_key=result.state_machine_key,
        state_machine_version=result.state_machine_version,
        object_type=result.object_type,
        object_id=result.object_id,
        from_state=result.from_state,
        to_state=result.to_state,
        validation_status=result.validation_status,
        is_valid=result.is_valid,
        reason=result.reason,
        validation_id=result.validation_id,
        terminal_transition=result.terminal_transition,
    )
