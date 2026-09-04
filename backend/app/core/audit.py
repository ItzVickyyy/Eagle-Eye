"""
Developer audit-log support.

This module provides a small, best-effort persistence boundary for audit
events so that Developer-visible logs reflect real application activity rather
than hardcoded sample records.

Design
------
- ``REDACT_KEYS`` / ``redact_sensitive`` establish a reusable sanitization
  boundary: sensitive key/value pairs are removed from any metadata before it
  reaches a stored log entry.
- ``write_audit_log`` persists an ``AuditLog`` row in the supplied session.
  It is deliberately defensive: if audit persistence itself fails, the
  underlying business operation is not broken (the error is logged via the
  standard logging module and swallowed). State-changing routes add the event
  to the same session so the event commits atomically with the operation.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.models import AuditLog, User

logger = logging.getLogger(__name__)

# Keys whose values must never be persisted to an audit log. Any matching
# metadata entry is scrubbed regardless of case and nesting depth.
REDACT_KEYS = frozenset(
    {
        "password",
        "password_confirmation",
        "current_password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "reset_token",
        "authorization",
        "cookie",
        "secret",
        "secret_key",
        "api_key",
        "client_secret",
        "smtp_password",
        "database_url",
        "postgres_password",
        "first_superuser_password",
    }
)

_REDACTED_LABEL = "[REDACTED]"


def _redact_value(key: str, value: Any) -> Any:
    if isinstance(key, str) and key.strip().lower() in REDACT_KEYS:
        return _REDACTED_LABEL
    return value


def redact_sensitive(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a scrubbed copy of ``payload`` with sensitive values removed.

    A redundant recursive walk keeps the audit trail free of credentials,
    tokens, headers, cookies, and environment secrets even when nested.
    """
    if not payload:
        return None

    def scrub(node: Any) -> Any:
        if isinstance(node, Mapping):
            cleaned: dict[str, Any] = {}
            for k, v in node.items():
                redacted = scrub(v)
                if isinstance(k, str) and k.strip().lower() in REDACT_KEYS:
                    cleaned[k] = _REDACTED_LABEL
                else:
                    cleaned[k] = redacted
            return cleaned
        if isinstance(node, (list, tuple)):
            return [scrub(item) for item in node]
        return node

    return dict(scrub(payload))


def write_audit_log(
    *,
    session: Session,
    event: str,
    message: str,
    severity: str = "INFO",
    component: str = "system",
    actor: User | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    success: bool = True,
) -> AuditLog | None:
    """Persist an audit event as a best-effort, non-blocking side effect.

    Returns the created ``AuditLog`` row, or ``None`` if persistence failed.
    The event row is added to ``session`` (it commits with the surrounding
    transaction), so a transient write error does not break the business op.
    """
    actor_id: UUID | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    actor_is_developer = False
    if actor is not None:
        actor_id = actor.id
        actor_email = actor.email
        actor_role = str(actor.role)
        actor_is_developer = bool(actor.is_developer)

    entry = AuditLog(
        event=event,
        severity=str(severity).upper(),
        component=component,
        actor_user_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        actor_is_developer=actor_is_developer,
        target_type=target_type,
        target_id=target_id,
        success=bool(success),
        message=str(message)[:2048],
    )
    try:
        session.add(entry)
        # Nothing is committed here on purpose: the caller commits with the
        # surrounding transaction so business state and audit state stay
        # consistent.
    except Exception:  # pragma: no cover - defensive only
        logger.exception("Failed to record audit event %s", event)
        session.rollback()
        return None
    return entry
