"""Pydantic v2 schemas for contracts and rate card endpoints.

CONTRACT-04: RateCardEntryResponse includes an optional margin field.
Margin (ceiling - cost_rate) is NEVER stored in the DB — computed at read time.
The API layer sets margin=None for Customer role, a Decimal value for SM/Recruiter/Admin.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ALLOWED_CONTRACT_STATUSES = {"active", "expired", "suspended"}


class ContractCreate(BaseModel):
    """Schema for creating a framework contract."""

    reference: str = Field(max_length=100)
    title: str = Field(max_length=255)
    lot_number: str | None = Field(default=None, max_length=50)
    start_date: date
    end_date: date
    max_value: Decimal | None = None
    currency: str = Field(default="EUR", max_length=3)
    status: str = "active"

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _ALLOWED_CONTRACT_STATUSES:
            raise ValueError(
                f"status must be one of: {sorted(_ALLOWED_CONTRACT_STATUSES)}"
            )
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ContractUpdate(BaseModel):
    """Schema for partially updating a framework contract. All fields optional."""

    reference: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=255)
    lot_number: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    max_value: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in _ALLOWED_CONTRACT_STATUSES:
            raise ValueError(
                f"status must be one of: {sorted(_ALLOWED_CONTRACT_STATUSES)}"
            )
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "ContractUpdate":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be on or after start_date")
        return self


class ContractResponse(BaseModel):
    """Full contract response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    reference: str
    title: str
    lot_number: str | None
    start_date: date
    end_date: date
    max_value: Decimal | None
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime


class RateCardEntryCreate(BaseModel):
    """Schema for creating a rate card entry under a contract."""

    profile_id: uuid.UUID
    sfia_level: int = Field(ge=1, le=7)
    max_daily_rate: Decimal = Field(gt=0)
    currency: str = Field(default="EUR", max_length=3)
    effective_from: date
    effective_to: date

    @model_validator(mode="after")
    def validate_date_range(self) -> "RateCardEntryCreate":
        if self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class RateCardEntryUpdate(BaseModel):
    """Schema for partially updating a rate card entry."""

    max_daily_rate: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=3)
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "RateCardEntryUpdate":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_to < self.effective_from:
                raise ValueError("effective_to must be on or after effective_from")
        return self


class RateCardEntryResponse(BaseModel):
    """Rate card entry response schema.

    CONTRACT-04: margin field is role-gated.
    - SM/Recruiter/Admin: margin = ceiling minus cost_rate (computed by API layer)
    - Customer: margin = None (field omitted from their perspective)
    margin is NOT stored in the DB — always computed at read time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_id: uuid.UUID
    profile_id: uuid.UUID
    sfia_level: int
    max_daily_rate: Decimal
    currency: str
    effective_from: date
    effective_to: date
    created_at: datetime
    # Computed field — NOT in ORM model. None for Customer role.
    margin: Decimal | None = None
