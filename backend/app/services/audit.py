"""Audit logging service.

Provides log_audit_event() — a simple INSERT helper for appending records
to the audit_log table. The caller is responsible for committing the session.

This is intentionally low-level: no business logic, no filtering.
All compliance-relevant actions should go through this function.

Audit log is append-only — no UPDATE or DELETE operations exist.
"""
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit_event(
    db: AsyncSession,
    action: str,
    *,
    tenant_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit log entry to the session (caller commits).

    Args:
        db:          AsyncSession — the record is added but NOT committed here.
        action:      Action name, e.g. 'approval.created', 'approval.approved',
                     'user.created', 'user.deactivated'.
        tenant_id:   Tenant context (nullable — some actions are cross-tenant).
        actor_id:    User who performed the action (nullable — system actions).
        entity_type: Type of entity being acted on, e.g. 'approval_request', 'user'.
        entity_id:   ID of the entity being acted on.
        payload:     Full context snapshot (dict). Defaults to empty dict.
        ip_address:  Originating IP address (IPv4 or IPv6, up to 45 chars).
    """
    entry = AuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload or {},
        ip_address=ip_address,
    )
    db.add(entry)
