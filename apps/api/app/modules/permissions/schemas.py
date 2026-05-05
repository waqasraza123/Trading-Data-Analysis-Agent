from app.core.schemas import ApiSchema
from app.modules.permissions.registry import Permission
from app.modules.users.models import UserRole


class PermissionDefinitionRead(ApiSchema):
    permission: Permission
    group: str
    description: str


class RolePermissionRead(ApiSchema):
    role: UserRole
    permissions: list[Permission]


class PermissionRegistryRead(ApiSchema):
    permissions: list[PermissionDefinitionRead]
    role_permissions: list[RolePermissionRead]
