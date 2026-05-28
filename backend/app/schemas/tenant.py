"""Pydantic v2 schemas for tenant CRUD and user-tenant assignment endpoints."""
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TenantCreate(BaseModel):
    """Schema for creating a new tenant.

    prefix must be 2-6 uppercase alphanumeric characters (e.g., 'ECTL', 'AB', 'XY1Z').
    """

    prefix: str
    name: str
    config: dict | None = None

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9]{2,6}$", v):
            raise ValueError(
                "prefix must be 2-6 uppercase alphanumeric characters (A-Z, 0-9)"
            )
        return v


class TenantUpdate(BaseModel):
    """Schema for partial tenant update.

    Prefix is immutable — cannot be changed after creation.
    Only name and config can be updated.
    """

    name: str | None = None
    config: dict | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prefix: str
    name: str
    config: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserTenantAssignRequest(BaseModel):
    """Schema for assigning a user to a tenant (body payload).

    tenant_id is also present in the path — this field is not required in the
    request body for the assign endpoint (tenant_id comes from path param),
    but kept here for flexibility.
    """

    user_id: uuid.UUID


class UserTenantAssignResponse(BaseModel):
    """Schema for user-tenant assignment response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    assigned_at: datetime


class UserBrief(BaseModel):
    """Brief user summary for tenant user listing."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    display_name: str | None
    is_active: bool
