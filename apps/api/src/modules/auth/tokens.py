"""
JWT token creation and validation for CampusAgent.

This module provides:
- ``TokenType``: enum for access and refresh token types.
- ``create_access_token(user_id, role, settings)``: create a short-lived access JWT.
- ``create_refresh_token(user_id, family_id, session_id, settings)``: create a
  long-lived refresh JWT with family/session claims.
- ``decode_token(token, settings)``: decode and validate a JWT.
- ``hash_jti(jti)``: SHA-256 hash of the ``jti`` claim for server-side storage.

Design principles:
- Tokens are signed with ``APP_SECRET`` from settings.
- Access tokens expire after ``ACCESS_TOKEN_EXPIRE_MINUTES`` (default 60).
- Refresh tokens expire after ``REFRESH_TOKEN_EXPIRE_DAYS`` (default 7).
- ``jti`` is a random UUID; only its hash is stored server-side.
- The raw JWT string is never stored or logged.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import jwt

from ...config import Settings
from ...db.time import utc_now


class TokenType(StrEnum):
    """JWT token type claim values."""

    ACCESS = "access"
    REFRESH = "refresh"


def _get_secret(settings: Settings) -> str:
    """Return the JWT signing key from settings."""
    return settings.APP_SECRET.get_secret_value()


def create_access_token(
    user_id: UUID,
    role: str,
    settings: Settings,
) -> tuple[str, str]:
    """Create a signed JWT access token.

    Args:
        user_id: The user's UUID.
        role: The user's global role (e.g. "STUDENT").
        settings: Application settings (for secret and expiry).

    Returns:
        A tuple of ``(token_string, jti)`` where ``jti`` is the unique
        token ID. The ``jti`` should be hashed before storage.
    """
    now = utc_now()
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "typ": TokenType.ACCESS.value,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }

    token = jwt.encode(payload, _get_secret(settings), algorithm="HS256")
    return token, jti


def create_refresh_token(
    user_id: UUID,
    family_id: str,
    session_id: UUID,
    settings: Settings,
) -> tuple[str, str, datetime]:
    """Create a signed JWT refresh token.

    Args:
        user_id: The user's UUID.
        family_id: The token family ID for replay detection.
        session_id: The AuthSession UUID.
        settings: Application settings (for secret and expiry).

    Returns:
        A tuple of ``(token_string, jti, expires_at)`` where ``jti`` is
        the unique token ID and ``expires_at`` is the expiry datetime.
    """
    now = utc_now()
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "typ": TokenType.REFRESH.value,
        "family_id": family_id,
        "session_id": str(session_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }

    token = jwt.encode(payload, _get_secret(settings), algorithm="HS256")
    return token, jti, exp


def decode_token(token: str, settings: Settings) -> dict[str, object]:
    """Decode and validate a JWT token.

    Args:
        token: The JWT string to decode.
        settings: Application settings (for secret).

    Returns:
        The decoded payload as a dict.

    Raises:
        jwt.PyJWTError: If the token is invalid, expired, or malformed.
    """
    return jwt.decode(token, _get_secret(settings), algorithms=["HS256"])


def hash_jti(jti: str) -> str:
    """Hash a JWT ``jti`` claim using SHA-256.

    Only the ``jti`` is hashed — never the entire token string.
    This hash is stored server-side for revocation and replay detection.

    Args:
        jti: The JWT ``jti`` claim value.

    Returns:
        The SHA-256 hex digest of the ``jti``.
    """
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()
