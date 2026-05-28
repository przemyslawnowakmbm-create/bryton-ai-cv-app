"""Pydantic v2 schemas for approval chain and audit log endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


_ALLOWED_APPROVAL_TYPES = {"shortlist_submission", "rate_override", "candidate_above_rate"}
_ALLOWED_DECISION_STATUSES = {"approved", "rejected", "changes_requested"}


class ApprovalCreate(BaseModel):
    """Schema for creating an approval request."""

    type: str
    justification: str
    context_data: dict = {}
    approver_id: uuid.UUID | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in _ALLOWED_APPROVAL_TYPES:
            raise ValueError(
                f"type must be one of: {sorted(_ALLOWED_APPROVAL_TYPES)}"
            )
        return v


class ApprovalDecision(BaseModel):
    """Schema for deciding on an approval request (approve, reject, or request changes)."""

    status: str
    decision_reason: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _ALLOWED_DECISION_STATUSES:
            raise ValueError(
                f"status must be one of: {sorted(_ALLOWED_DECISION_STATUSES)}"
            )
        return v


class ApprovalResponse(BaseModel):
    """Full approval request response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    requester_id: uuid.UUID
    approver_id: uuid.UUID | None
    type: str
    status: str
    context_data: dict
    justification: str
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None


class AuditLogResponse(BaseModel):
    """Audit log entry response schema (Admin query)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    action: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    payload: dict
    ip_address: str | None
    created_at: datetime
