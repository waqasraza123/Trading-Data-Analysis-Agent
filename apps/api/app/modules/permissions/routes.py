from fastapi import APIRouter

from app.modules.permissions.schemas import PermissionRegistryRead, RolePermissionRead
from app.modules.permissions.service import permission_definitions, role_permission_definitions
from app.modules.users.models import UserRole

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=PermissionRegistryRead)
async def get_permission_registry() -> PermissionRegistryRead:
    return PermissionRegistryRead(
        permissions=permission_definitions(),
        role_permissions=role_permission_definitions(),
    )


@router.get("/roles/{role}", response_model=RolePermissionRead)
async def get_role_permissions(role: UserRole) -> RolePermissionRead:
    role_permissions = {item.role: item for item in role_permission_definitions()}
    return role_permissions[role]
