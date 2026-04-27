"""Centralised audit log writes."""

from __future__ import annotations

from app.enums import AuditAction
from app.extensions import db
from app.models import AuditLog


def record_audit(
    user_id: int | None,
    action: AuditAction,
    details: str | None = None,
) -> None:
    """Add an audit log record."""
    db.session.add(AuditLog(user_id=user_id, action=action, details=details))
