from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

from .repository import SafetyPolicyRepository
from .schemas import (
    EvaluateActionRequest,
    EvaluatePayloadRequest,
    EvaluateTextRequest,
    SafetyEvaluationResponse,
    SafetyPolicySetRead,
)
from .service import SafetyPolicyService

router = APIRouter(prefix="/safety-policies", tags=["safety-policies"])


def get_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SafetyPolicyService:
    return SafetyPolicyService(SafetyPolicyRepository(session))


@router.get("", response_model=list[SafetyPolicySetRead])
async def list_safety_policies(
    service: Annotated[SafetyPolicyService, Depends(get_service)],
    workspace_id: str | None = None,
) -> list[SafetyPolicySetRead]:
    if service.repository is None:
        return []
    policy_sets = await service.repository.list_policy_sets(workspace_id)
    return [
        SafetyPolicySetRead(
            id=policy_set.id,
            workspaceId=policy_set.workspace_id,
            key=policy_set.key,
            version=policy_set.version,
            status=policy_set.status,
            description=policy_set.description,
            policyJson=policy_set.policy_json,
            createdAt=policy_set.created_at.isoformat() if policy_set.created_at else None,
            updatedAt=policy_set.updated_at.isoformat() if policy_set.updated_at else None,
        )
        for policy_set in policy_sets
    ]


@router.get("/{key}/{version}", response_model=SafetyPolicySetRead)
async def get_safety_policy(
    key: str,
    version: str,
    service: Annotated[SafetyPolicyService, Depends(get_service)],
    workspace_id: str | None = None,
) -> SafetyPolicySetRead:
    if service.repository is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Safety policy set not found."
        )
    policy_set = await service.repository.get_policy_set(
        key=key, version=version, workspace_id=workspace_id
    )
    if policy_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Safety policy set not found."
        )
    return SafetyPolicySetRead(
        id=policy_set.id,
        workspaceId=policy_set.workspace_id,
        key=policy_set.key,
        version=policy_set.version,
        status=policy_set.status,
        description=policy_set.description,
        policyJson=policy_set.policy_json,
        createdAt=policy_set.created_at.isoformat() if policy_set.created_at else None,
        updatedAt=policy_set.updated_at.isoformat() if policy_set.updated_at else None,
    )


@router.post(
    "/seed-default",
    dependencies=[Depends(require_permission(Permission.SAFETY_POLICIES_ADMIN))],
)
async def seed_default_safety_policy(
    service: Annotated[SafetyPolicyService, Depends(get_service)],
    workspace_id: str | None = None,
) -> dict[str, str]:
    policy = await service.seed_default_policy_set(workspace_id)
    return {"key": policy.key, "version": policy.version, "status": policy.status.value}


@router.post("/evaluate-text", response_model=SafetyEvaluationResponse)
async def evaluate_text(
    request: EvaluateTextRequest,
    service: Annotated[SafetyPolicyService, Depends(get_service)],
) -> SafetyEvaluationResponse:
    return await service.evaluate_text(
        text=request.text,
        workspace_id=request.workspace_id,
        source_type=request.source_type,
        source_id=request.source_id,
    )


@router.post("/evaluate-action", response_model=SafetyEvaluationResponse)
async def evaluate_action(
    request: EvaluateActionRequest,
    service: Annotated[SafetyPolicyService, Depends(get_service)],
) -> SafetyEvaluationResponse:
    return await service.evaluate_action(
        action=request.action,
        workspace_id=request.workspace_id,
        source_type=request.source_type,
        source_id=request.source_id,
        context=request.context,
    )


@router.post("/evaluate-payload", response_model=SafetyEvaluationResponse)
async def evaluate_payload(
    request: EvaluatePayloadRequest,
    service: Annotated[SafetyPolicyService, Depends(get_service)],
) -> SafetyEvaluationResponse:
    return await service.evaluate_payload(
        payload=request.payload,
        workspace_id=request.workspace_id,
        source_type=request.source_type,
        source_id=request.source_id,
        public_response=request.public_response,
    )
