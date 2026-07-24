"""
Pydantic schemas for the auth module.

Request/response schemas for:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/auth/me

All schemas exclude password_hash and token strings from responses.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Request body for POST /api/v1/auth/register."""

    email: EmailStr
    password: str = Field(description="密码强度由服务层校验")
    display_name: str = Field(min_length=1, max_length=100)
    student_no: str = Field(min_length=1, max_length=50)
    phone_number: str | None = Field(
        default=None,
        min_length=7,
        max_length=24,
        pattern=r"^\+?[0-9][0-9 -]{5,22}[0-9]$",
        description="绑定手机，仅用于账号安全与本人通知",
    )
    organization_ids: list[UUID] = Field(
        default_factory=list,
        description="P3 接受但不创建成员关系",
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Shared response schemas
# ---------------------------------------------------------------------------


class UserRead(BaseModel):
    """User public fields returned by register, login, refresh, and me.

    Never includes password_hash or token strings.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    global_role: str


class RefreshResponse(BaseModel):
    """Response body for POST /api/v1/auth/refresh."""

    id: UUID
    email: str
    display_name: str
    global_role: str
    session_version: int
