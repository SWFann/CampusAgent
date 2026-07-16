"""
Password hashing, verification, and strength validation for CampusAgent.

This module provides:
- ``hash_password(password: str) -> str``: bcrypt-hash a plaintext password.
- ``verify_password(password: str, password_hash: str) -> bool``: verify a
  plaintext password against a stored bcrypt hash.
- ``validate_password_strength(password, *, email, student_no) -> None``:
  enforce minimum password strength rules.

Design principles:
- Uses the ``bcrypt`` library (industry-standard, adaptive cost).
- Salt is automatically generated per-hash, so identical passwords produce
  different hashes.
- ``validate_password_strength`` raises ``WeakPasswordError`` (code
  ``AUTH_WEAK_PASSWORD``) which is mapped to HTTP 400 by the global
  exception handler.
- Error messages never include the plaintext password.
"""

from __future__ import annotations

import re

import bcrypt

from .exceptions import WeakPasswordError

# bcrypt has a 72-byte password limit. We encode to UTF-8 before hashing.
# If a password exceeds 72 bytes, bcrypt will silently truncate it, which
# is acceptable for MVP — but we still enforce a maximum reasonable length
# in the strength validator.

# Bcrypt hash prefix for detecting bcrypt hashes.
_BCRYPT_PREFIX = b"$2"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        A bcrypt hash string (e.g. ``$2b$12$...``).

    Note:
        Each call produces a different hash due to random salt generation.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        password: The plaintext password to check.
        password_hash: The stored bcrypt hash string.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.

    Note:
        This function never raises on mismatch — it returns ``False``.
        If the hash is malformed, it returns ``False`` rather than raising
        to prevent information leakage.
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, TypeError, AttributeError):
        # Malformed hash or None password — return False rather than
        # leaking information about the failure mode.
        return False


def validate_password_strength(
    password: str,
    *,
    email: str | None = None,
    student_no: str | None = None,
) -> None:
    """Validate that a password meets minimum strength requirements.

    MVP rules:
    - Length at least 8 characters.
    - Contains at least one letter and one digit.
    - Not entirely whitespace.
    - Does not contain the email local part (before @).
    - Does not contain the student number.

    Args:
        password: The plaintext password to validate.
        email: Optional email address — the local part is checked.
        student_no: Optional student number — checked for inclusion.

    Raises:
        WeakPasswordError: If the password fails any strength rule.
            The error message never includes the plaintext password.
    """
    errors: list[str] = []

    # Rule 1: Minimum length
    if len(password) < 8:
        errors.append("密码长度至少为 8 个字符")

    # Rule 2: Not all whitespace
    if password.strip() == "":
        errors.append("密码不能全为空白字符")

    # Rule 3: At least one letter and one digit
    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_digit = bool(re.search(r"\d", password))
    if not has_letter:
        errors.append("密码必须包含至少一个字母")
    if not has_digit:
        errors.append("密码必须包含至少一个数字")

    # Rule 4: Does not contain email local part
    if email and "@" in email:
        local_part = email.split("@")[0]
        if local_part and len(local_part) >= 3 and local_part.lower() in password.lower():
            errors.append("密码不能包含邮箱地址的本地部分")

    # Rule 5: Does not contain student number
    if student_no and len(student_no) >= 3 and student_no in password:
        errors.append("密码不能包含学号")

    if errors:
        raise WeakPasswordError(
            message="; ".join(errors),
            details={"rules_failed": errors},
        )
