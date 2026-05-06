from enum import StrEnum

from app.config import Settings


class AuthMode(StrEnum):
    DEV = "dev"
    API_KEY = "api_key"
    JWT = "jwt"
    MIXED = "mixed"


def effective_auth_mode(settings: Settings) -> AuthMode:
    mode = AuthMode(settings.auth_mode)
    if settings.auth_enabled and mode == AuthMode.DEV:
        return AuthMode.API_KEY
    return mode


def auth_is_enforced(settings: Settings) -> bool:
    return settings.auth_enabled or effective_auth_mode(settings) != AuthMode.DEV
