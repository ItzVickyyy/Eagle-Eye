"""JWT revocation and token-version helpers.

The two-layer strategy:

1. **Per-user token version** (``User.token_version``): a monotonically
   increasing integer. When it is bumped, every token with an older ``tv``
   claim is rejected immediately in ``get_current_user`` with zero extra
   queries. This is used for bulk invalidation (password change, password
   reset).

2. **Per-jti denylist** (``TokenRevocation`` table): stores the explicit
   ``jti`` of a single token that the user logged out of. This is the only
   way to kill a *specific* session without affecting the user's other
   devices.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlmodel import Session, delete, select

from app.models import TokenRevocation, User

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Per-jti revocation                                                  #
# ------------------------------------------------------------------ #


def revoke_token(
    *,
    session: Session,
    jti: str,
    user_id: str | object,
    expires_at: datetime,
    reason: str = "logout",
) -> None:
    """Insert a revocation row for a specific ``jti``.

    If the ``jti`` is already revoked the call is idempotent — the existing
    row is left untouched and no exception is raised.
    """
    existing = session.exec(
        select(TokenRevocation.jti).where(TokenRevocation.jti == jti).limit(1)
    ).first()
    if existing is not None:
        return
    row = TokenRevocation(
        jti=jti,
        user_id=user_id,  # type: ignore[arg-type]
        expires_at=expires_at,
        reason=reason,
    )
    session.add(row)


def is_token_revoked(session: Session, jti: str) -> bool:
    """Return True when ``jti`` is in the active (unexpired) denylist."""
    now = datetime.now(UTC)
    stmt = (
        select(TokenRevocation.jti)
        .where(
            TokenRevocation.jti == jti,
            TokenRevocation.expires_at > now,
        )
        .limit(1)
    )
    return session.exec(stmt).first() is not None


# ------------------------------------------------------------------ #
# Per-user token version                                              #
# ------------------------------------------------------------------ #


def bump_token_version(*, session: Session, user: User) -> None:
    """Increment ``User.token_version``, invalidating all of its tokens.

    The column is backed by ``server_default='0'`` and is guaranteed to be
    present for every existing row (see migration).
    """
    user.token_version = (user.token_version or 0) + 1
    session.add(user)


# ------------------------------------------------------------------ #
# Startup GC                                                          #
# ------------------------------------------------------------------ #


def prune_revocations(session: Session) -> None:
    """Delete revocation rows whose ``expires_at`` has passed.

    Called once at FastAPI startup. The hot path already filters on
    ``expires_at > now()`` so stale rows are harmless from a correctness
    standpoint; pruning only keeps the table size bounded.
    """
    now = datetime.now(UTC)
    deleted = session.exec(
        delete(TokenRevocation).where(TokenRevocation.expires_at <= now)
    )
    try:
        session.commit()
        logger.info("Pruned %d expired token revocation rows", deleted.rowcount)
    except Exception:  # pragma: no cover — best-effort
        logger.exception("Failed to prune expired token revocations")
        session.rollback()
