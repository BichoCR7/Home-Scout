"""Short-lived signed access tokens and random high-entropy secret helpers."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt


class InvalidAccessToken(ValueError):
    """A token failed verification or did not contain the required claims."""


class AccessTokenCodec:
    issuer = "homescout-api"
    audience = "homescout-android"

    def __init__(self, signing_key: str, *, lifetime_seconds: int) -> None:
        if len(signing_key.encode("utf-8")) < 32:
            raise ValueError("Authentication signing keys must contain at least 32 bytes.")
        self._signing_key = signing_key
        self._lifetime_seconds = lifetime_seconds

    def issue(self, *, user_id: UUID, session_id: UUID) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._lifetime_seconds)
        token = jwt.encode(
            {
                "sub": str(user_id),
                "sid": str(session_id),
                "jti": str(uuid4()),
                "iat": now,
                "nbf": now,
                "exp": expires_at,
                "iss": self.issuer,
                "aud": self.audience,
                "token_use": "access",
            },
            self._signing_key,
            algorithm="HS256",
        )
        return token, expires_at

    def decode(self, token: str) -> dict[str, object]:
        try:
            claims = jwt.decode(
                token,
                self._signing_key,
                algorithms=["HS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["sub", "sid", "jti", "iat", "nbf", "exp", "iss", "aud"],
                },
            )
            if claims.get("token_use") != "access":
                raise InvalidAccessToken("Wrong token purpose.")
            UUID(str(claims["sub"]))
            UUID(str(claims["sid"]))
            return claims
        except (jwt.InvalidTokenError, KeyError, ValueError, TypeError) as exc:
            raise InvalidAccessToken("Invalid access token.") from exc


def new_secret() -> str:
    """Create a URL-safe, 256-bit random one-time or refresh token."""

    return secrets.token_urlsafe(32)


def secret_digest(secret: str) -> str:
    """Store a fast one-way digest only for high-entropy random secrets."""

    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
