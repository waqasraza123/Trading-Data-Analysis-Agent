import base64
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config import Settings
from app.core.errors import AppError


class JwtVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify(self, token: str) -> dict[str, object]:
        if not self.settings.auth_jwt_enabled:
            raise AppError(401, "jwt_disabled", "JWT authentication is disabled")
        if self.settings.jwt_public_key is None:
            raise AppError(500, "jwt_not_configured", "JWT verification is not configured")
        header, payload, signed_part, signature = parse_jwt(token)
        algorithm = str(header.get("alg", ""))
        if algorithm != self.settings.jwt_algorithm:
            raise AppError(401, "invalid_token", "Token algorithm is invalid")
        public_key = serialization.load_pem_public_key(
            self.settings.jwt_public_key.get_secret_value().encode("utf-8")
        )
        public_key.verify(signature, signed_part, padding.PKCS1v15(), hashes.SHA256())
        validate_claims(payload, self.settings)
        return payload


def parse_jwt(token: str) -> tuple[dict[str, object], dict[str, object], bytes, bytes]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AppError(401, "invalid_token", "Token format is invalid")
    header = decode_json_part(parts[0])
    payload = decode_json_part(parts[1])
    signed_part = f"{parts[0]}.{parts[1]}".encode("ascii")
    signature = decode_base64_url(parts[2])
    return header, payload, signed_part, signature


def decode_json_part(value: str) -> dict[str, object]:
    decoded = decode_base64_url(value)
    try:
        payload = json.loads(decoded.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AppError(401, "invalid_token", "Token payload is invalid") from error
    if not isinstance(payload, dict):
        raise AppError(401, "invalid_token", "Token payload is invalid")
    return payload


def decode_base64_url(value: str) -> bytes:
    padding_length = (-len(value)) % 4
    try:
        return base64.urlsafe_b64decode(f"{value}{'=' * padding_length}".encode("ascii"))
    except ValueError as error:
        raise AppError(401, "invalid_token", "Token encoding is invalid") from error


def validate_claims(claims: Mapping[str, Any], settings: Settings) -> None:
    now = int(datetime.now(UTC).timestamp())
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise AppError(401, "invalid_token", "Token subject is missing")
    issuer = claims.get("iss")
    if settings.jwt_issuer and issuer != settings.jwt_issuer:
        raise AppError(401, "invalid_token", "Token issuer is invalid")
    audience = claims.get("aud")
    if settings.jwt_audience and not audience_matches(audience, settings.jwt_audience):
        raise AppError(401, "invalid_token", "Token audience is invalid")
    expires_at = claims.get("exp")
    if isinstance(expires_at, int | float) and int(expires_at) < now:
        raise AppError(401, "token_expired", "Token has expired")
    not_before = claims.get("nbf")
    if isinstance(not_before, int | float) and int(not_before) > now:
        raise AppError(401, "invalid_token", "Token is not valid yet")


def audience_matches(audience: object, expected: str) -> bool:
    if isinstance(audience, str):
        return audience == expected
    if isinstance(audience, list):
        return expected in audience
    return False
