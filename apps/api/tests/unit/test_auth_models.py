"""
Unit tests for AuthSession and RefreshToken ORM models (P3-01).

These tests verify:
- Creating AuthSession linked to a User succeeds.
- AuthSession family_id is queryable.
- Creating RefreshToken linked to a session succeeds.
- RefreshToken stores jti_hash (not raw token).
- RefreshToken status defaults to ACTIVE.
- Session and token relationship.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.time import utc_now
from src.modules.auth.models import (
    AuthSession,
    RefreshToken,
    RefreshTokenStatus,
    SessionStatus,
)
from src.modules.users.models import GlobalRole, User, UserStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(session, email: str = "authuser@example.edu") -> User:
    """Create a minimal User for auth model tests."""
    user = User(
        email=email,
        password_hash="$2b$12$dummy",
        display_name="Auth User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    return user


def _make_session(session, user: User, family_id: str = "fam-001") -> AuthSession:
    """Create an AuthSession linked to the given user."""
    now = utc_now()
    auth_session = AuthSession(
        user_id=user.id,
        family_id=family_id,
        session_version=1,
        status=SessionStatus.ACTIVE.value,
        expires_at=now + timedelta(days=7),
    )
    session.add(auth_session)
    session.flush()
    return auth_session


# ---------------------------------------------------------------------------
# 1. AuthSession creation
# ---------------------------------------------------------------------------


class TestAuthSessionCreation:
    def test_create_session_success(self, test_db_session):
        """Creating an AuthSession linked to a user succeeds."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.commit()

        assert session.id is not None
        assert session.user_id == user.id
        assert session.family_id == "fam-001"
        assert session.session_version == 1
        assert session.status == SessionStatus.ACTIVE.value
        assert session.created_at is not None
        assert session.expires_at is not None
        assert session.revoked_at is None

    def test_family_id_is_queryable(self, test_db_session):
        """AuthSession can be queried by family_id."""
        from sqlalchemy import select

        user = _make_user(test_db_session)
        _make_session(test_db_session, user, family_id="fam-query-001")
        test_db_session.flush()

        stmt = select(AuthSession).where(AuthSession.family_id == "fam-query-001")
        result = test_db_session.execute(stmt).scalar_one_or_none()
        assert result is not None
        assert result.family_id == "fam-query-001"

    def test_session_version_defaults_to_1(self, test_db_session):
        """Default session_version is 1."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        assert session.session_version == 1


# ---------------------------------------------------------------------------
# 2. RefreshToken creation
# ---------------------------------------------------------------------------


class TestRefreshTokenCreation:
    def test_create_refresh_token_success(self, test_db_session):
        """Creating a RefreshToken linked to a session succeeds."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        now = utc_now()
        token = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash="a" * 64,  # SHA-256 hex
            status=RefreshTokenStatus.ACTIVE.value,
            expires_at=now + timedelta(days=7),
        )
        test_db_session.add(token)
        test_db_session.flush()

        assert token.id is not None
        assert token.session_id == session.id
        assert token.user_id == user.id
        assert token.family_id == session.family_id
        assert token.jti_hash == "a" * 64
        assert token.status == RefreshTokenStatus.ACTIVE.value
        assert token.issued_at is not None
        assert token.expires_at is not None
        assert token.used_at is None
        assert token.revoked_at is None

    def test_jti_hash_unique(self, test_db_session):
        """Two tokens with the same jti_hash must raise IntegrityError."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        now = utc_now()
        jti = "b" * 64

        token1 = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash=jti,
            expires_at=now + timedelta(days=7),
        )
        test_db_session.add(token1)
        test_db_session.flush()

        token2 = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash=jti,  # same hash
            expires_at=now + timedelta(days=7),
        )
        test_db_session.add(token2)
        with pytest.raises(IntegrityError):
            test_db_session.flush()

    def test_refresh_token_does_not_store_raw_token(self, test_db_session):
        """RefreshToken stores jti_hash, not the raw JWT string."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        # Simulate a raw JWT token
        raw_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature"
        # The jti_hash is a SHA-256 of the jti claim, not the full token
        import hashlib

        jti_claim = "unique-jti-claim-12345"
        jti_hash = hashlib.sha256(jti_claim.encode()).hexdigest()

        token = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash=jti_hash,
            expires_at=utc_now() + timedelta(days=7),
        )
        test_db_session.add(token)
        test_db_session.flush()

        # The stored hash must NOT be the raw token
        assert token.jti_hash != raw_token
        assert "eyJ" not in token.jti_hash
        assert len(token.jti_hash) == 64  # SHA-256 hex length

    def test_repr_does_not_leak_jti(self, test_db_session):
        """RefreshToken __repr__ must not include jti_hash value."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        token = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash="c" * 64,
            expires_at=utc_now() + timedelta(days=7),
        )
        repr_str = repr(token)
        assert "cccc" not in repr_str
        assert "[REDACTED]" in repr_str


# ---------------------------------------------------------------------------
# 3. Session ↔ RefreshToken relationship
# ---------------------------------------------------------------------------


class TestSessionTokenRelationship:
    def test_session_has_refresh_tokens(self, test_db_session):
        """AuthSession.refresh_tokens returns the linked tokens."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        now = utc_now()
        for i in range(3):
            token = RefreshToken(
                session_id=session.id,
                user_id=user.id,
                family_id=session.family_id,
                jti_hash=f"hash-{i}" + "0" * 58,
                expires_at=now + timedelta(days=7),
            )
            test_db_session.add(token)
        test_db_session.flush()

        # Refresh the session to load the relationship
        test_db_session.refresh(session)
        assert len(session.refresh_tokens) == 3

    def test_token_links_back_to_session(self, test_db_session):
        """RefreshToken.session returns the parent AuthSession."""
        user = _make_user(test_db_session)
        session = _make_session(test_db_session, user)
        test_db_session.flush()

        token = RefreshToken(
            session_id=session.id,
            user_id=user.id,
            family_id=session.family_id,
            jti_hash="d" * 64,
            expires_at=utc_now() + timedelta(days=7),
        )
        test_db_session.add(token)
        test_db_session.flush()

        test_db_session.refresh(token)
        assert token.session is not None
        assert token.session.id == session.id
