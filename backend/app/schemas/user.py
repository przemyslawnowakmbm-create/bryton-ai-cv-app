"""Pydantic v2 schemas for user management endpoints (Admin CRUD + SM tenant-scoped)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


_ALLOWED_ROLES = {"admin", "sm", "recruiter", "customer", "candidate"}


class UserCreate(BaseModel):
    """Schema for Admin creating a user of any role.

    email_verified is set to True on Admin-created users (skip verification flow).
    If role is customer or candidate, tenant_id is required.
    If role is sm or recruiter and tenant_id is provided, a UserTenantAssignment
    is also created.
    """

    email: EmailStr
    password: str
    role: str
    display_name: str | None = None
    tenant_id: uuid.UUID | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in _ALLOWED_ROLES:
            raise ValueError(
                f"role must be one of: {sorted(_ALLOWED_ROLES)}"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    """Schema for partial user update.

    Only provided (non-None) fields are applied. role is validated if provided.
    If role changes to customer or candidate, the calling endpoint must verify tenant_id is set.
    """

    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    tenant_id: uuid.UUID | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_ROLES:
            raise ValueError(
                f"role must be one of: {sorted(_ALLOWED_ROLES)}"
            )
        return v


class UserResponse(BaseModel):
    """Full user response schema returned by Admin endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    display_name: str | None
    is_active: bool
    email_verified: bool
    tenant_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class UserBrief(BaseModel):
    """Brief user summary used in list contexts."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    display_name: str | None
    is_active: bool
