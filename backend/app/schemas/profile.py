"""Pydantic v2 schemas for profile catalogue, profile requirements, and compliance.

PROFILE-01: Profile catalogue schemas with SFIA range validation.
PROFILE-02: DemandDefaultsResponse for demand pre-population.
PROFILE-03: ProfileDiffResponse for field-level deviation tracking.
PROFILE-04: ComplianceCheckResponse for advisory compliance checking.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ALLOWED_REQ_TYPES = {"skill", "certification", "language", "clearance", "education"}


class ProfileRequirementCreate(BaseModel):
    """Schema for creating a profile requirement."""

    req_type: str
    description: str = Field(max_length=255)
    is_mandatory: bool = True
    # Only populated when req_type='language' (CEFR levels: A1, A2, B1, B2, C1, C2)
    min_cefr_level: str | None = Field(default=None, max_length=2)

    @field_validator("req_type")
    @classmethod
    def validate_req_type(cls, v: str) -> str:
        if v not in _ALLOWED_REQ_TYPES:
            raise ValueError(
                f"req_type must be one of: {sorted(_ALLOWED_REQ_TYPES)}"
            )
        return v


class ProfileRequirementResponse(BaseModel):
    """Full profile requirement response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    profile_id: uuid.UUID
    tenant_id: uuid.UUID
    req_type: str
    description: str
    is_mandatory: bool
    min_cefr_level: str | None
    created_at: datetime


class ProfileCreate(BaseModel):
    """Schema for creating a profile catalogue entry.

    PROFILE-01: Supports code, title, SFIA range, min experience, clearance, education.
    Nested requirements are created atomically with the profile.
    """

    contract_id: uuid.UUID | None = None
    code: str = Field(max_length=20)
    title: str = Field(max_length=255)
    description: str | None = None
    sfia_level_min: int = Field(ge=1, le=7)
    sfia_level_max: int = Field(ge=1, le=7)
    min_years_exp: int = Field(default=0, ge=0)
    min_education: str | None = Field(default=None, max_length=50)
    required_clearance: str | None = Field(default=None, max_length=20)
    # Nested requirements — created atomically with the profile
    requirements: list[ProfileRequirementCreate] = []

    @model_validator(mode="after")
    def validate_sfia_range(self) -> "ProfileCreate":
        if self.sfia_level_max < self.sfia_level_min:
            raise ValueError("sfia_level_max must be greater than or equal to sfia_level_min")
        return self


class ProfileUpdate(BaseModel):
    """Schema for partially updating a profile catalogue entry.

    Note: code is immutable — changing a profile code breaks rate card references.
    """

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    sfia_level_min: int | None = Field(default=None, ge=1, le=7)
    sfia_level_max: int | None = Field(default=None, ge=1, le=7)
    min_years_exp: int | None = Field(default=None, ge=0)
    min_education: str | None = Field(default=None, max_length=50)
    required_clearance: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_sfia_range(self) -> "ProfileUpdate":
        if self.sfia_level_min is not None and self.sfia_level_max is not None:
            if self.sfia_level_max < self.sfia_level_min:
                raise ValueError("sfia_level_max must be greater than or equal to sfia_level_min")
        return self


class ProfileResponse(BaseModel):
    """Full profile catalogue response schema with nested requirements."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    contract_id: uuid.UUID | None
    code: str
    title: str
    description: str | None
    sfia_level_min: int
    sfia_level_max: int
    min_years_exp: int
    min_education: str | None
    required_clearance: str | None
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    requirements: list[ProfileRequirementResponse] = []


class DemandDefaultsResponse(BaseModel):
    """Pre-fill dict for demand creation from a profile.

    PROFILE-02: Returned by GET /api/profiles/{id}/demand-defaults.
    All pre-populated fields are freely editable by the user — not locked.
    """

    sfia_level_min: int
    sfia_level_max: int
    min_years_exp: int
    required_skills: str | None
    min_education: str | None
    required_clearance: str | None
    # Derived from language requirements
    languages: list[dict[str, Any]] = []
    # Derived from certification requirements
    certifications: list[str] = []
    # Full serialised profile for storing in demand.profile_snapshot
    profile_snapshot: dict[str, Any]


class ProfileDiffEntry(BaseModel):
    """Single field deviation between profile template and demand."""

    field: str
    profile_value: Any
    demand_value: Any


class ProfileDiffResponse(BaseModel):
    """PROFILE-03: Diff between demand fields and source profile snapshot."""

    deviations: list[ProfileDiffEntry]
    has_deviations: bool


class ComplianceItem(BaseModel):
    """Result for a single profile requirement compliance check."""

    req_id: uuid.UUID
    req_type: str
    description: str
    is_mandatory: bool
    # Values: MET, PARTIALLY_MET, NOT_MET
    status: str


class ComplianceCheckResponse(BaseModel):
    """PROFILE-04: Advisory compliance check result.

    overall: NOT_MET if any mandatory requirement is NOT_MET;
             PARTIALLY_MET if any requirement is PARTIALLY_MET;
             MET if all requirements are satisfied.
    Advisory only — does not block shortlisting.
    """

    # Values: MET, PARTIALLY_MET, NOT_MET
    overall: str
    items: list[ComplianceItem]
