from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from .repository import SafetyPolicyRepository
from .schemas import EvaluateActionRequest, EvaluatePayloadRequest, EvaluateTextRequest, SafetyEvaluationResponse, SafetyPolicySetRead
from .service import SafetyPolicyService


router = APIRouter(prefix="/safety-policies", tags=["safety-policies"])


def _resolve_session_dependency() -> Any | None:
    candidates = (
        ("app.database", "get_db"),
        ("app.database", "get_session"),
        ("app.db", "get_db"),
        ("app.db", "get_session"),
        ("app.core.database", "get_db"),
        ("app.core.database", "get_session"),
        ("app.core.db", "get_db"),
        ("app.core.db", "get_session"),
    )
    for module_name, attribute_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        dependency = getattr(module, attribute_name, None)
        if dependency is not None:
            return dependency
    return None


_session_dependency = _resolve_session_dependency()


async def _missing_session_dependency() -> AsyncIterator[Any]:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database session dependency is not configured for safety policies.",
    )
    yield None


get_session = _session_dependency or _missing_session_dependency


def get_service(session: Any = Depends(get_session)) -> SafetyPolicyService:
    return SafetyPolicyService(SafetyPolicyRepository(session))


@router.get("", response_model=list[SafetyPolicySetRead])
async def list_safety_policies(
    workspace_id: str | None = None,
    service: SafetyPolicyService = Depends(get_service),
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
    workspace_id: str | None = None,
    service: SafetyPolicyService = Depends(get_service),
) -> SafetyPolicySetRead:
    if service.repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety policy set not found.")
    policy_set = await service.repository.get_policy_set(key=key, version=version, workspace_id=workspace_id)
    if policy_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety policy set not found.")
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


@router.post("/seed-default")
async def seed_default_safety_policy(
    workspace_id: str | None = None,
    service: SafetyPolicyService = Depends(get_service),
) -> dict[str, str]:
    policy = await service.seed_default_policy_set(workspace_id)
    return {"key": policy.key, "version": policy.version, "status": policy.status.value}


@router.post("/evaluate-text", response_model=SafetyEvaluationResponse)
async def evaluate_text(
    request: EvaluateTextRequest,
    service: SafetyPolicyService = Depends(get_service),
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
    service: SafetyPolicyService = Depends(get_service),
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
    service: SafetyPolicyService = Depends(get_service),
) -> SafetyEvaluationResponse:
    return await service.evaluate_payload(
        payload=request.payload,
        workspace_id=request.workspace_id,
        source_type=request.source_type,
        source_id=request.source_id,
        public_response=request.public_response,
    )

