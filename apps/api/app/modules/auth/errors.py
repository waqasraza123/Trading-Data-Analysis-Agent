from app.core.errors import AppError


def authentication_required() -> AppError:
    return AppError(401, "authentication_required", "Authentication is required")


def invalid_credentials() -> AppError:
    return AppError(401, "invalid_credentials", "Credentials are invalid")


def invalid_user_context() -> AppError:
    return AppError(401, "invalid_user_context", "User context is invalid")


def forbidden() -> AppError:
    return AppError(403, "permission_denied", "Permission denied")


def workspace_access_denied() -> AppError:
    return AppError(403, "workspace_access_denied", "Workspace access denied")
