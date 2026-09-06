"""Runtime feature-flag enforcement tests (Implementation 17, Phase 2).

These tests cover the Developer feature-flag set:
  * ``dev_maintenance_mode``         — ``MaintenanceModeMiddleware``
  * ``dev_public_comments_enabled``  — public ``POST /api/v1/comments/``
  * ``dev_contact_form_enabled``     — public ``POST /api/v1/contact/``
  * ``dev_allow_public_signup``      — public ``POST /api/v1/users/signup``

Scope is intentionally narrow: only the flag-enforcement layer. The flag
mutation endpoint itself is covered by ``test_developer.py``.

The test DB is session-scoped (see ``tests/conftest.py``) and shared with
the rest of the suite, so every test must defensively restore the four
flag rows to their default state in a ``finally`` block.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.flags import (
    DEFAULT_FLAG_VALUES,
    FLAG_ALLOW_PUBLIC_SIGNUP,
    FLAG_CONTACT_FORM_ENABLED,
    FLAG_MAINTENANCE_MODE,
    FLAG_PUBLIC_COMMENTS_ENABLED,
)
from app.models import (
    ArticleStatus,
    SiteSetting,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string

# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------


def _set_flag(session: Session, key: str, value: bool) -> None:
    """Create or update a single flag row."""
    existing = session.get(SiteSetting, key)
    if existing is None:
        session.add(SiteSetting(key=key, value="true" if value else "false"))
    else:
        existing.value = "true" if value else "false"
    session.commit()


def _reset_all_flags(session: Session) -> None:
    """Restore every Developer flag to its documented default."""
    for key, default in DEFAULT_FLAG_VALUES.items():
        _set_flag(session, key, default)


def _make_developer_headers(
    client: TestClient, db: Session
) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            password=password,
            role=UserRole.contributor,
            is_developer=True,
        ),
    )
    return authentication_token_from_email(client=client, email=email, db=db)


def _make_admin_headers(
    client: TestClient, db: Session
) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            password=password,
            role=UserRole.admin,
        ),
    )
    return authentication_token_from_email(client=client, email=email, db=db)


def _make_article_with_admin(
    client: TestClient, db: Session
) -> str:
    """Create a Category + Article and return the article id as a string."""
    admin_headers = _make_admin_headers(client, db)
    cat_slug = f"test-cat-{uuid.uuid4().hex[:8]}"
    cat_resp = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=admin_headers,
        json={
            "name": f"Test {cat_slug}",
            "slug": cat_slug,
            "description": "Test category",
        },
    )
    assert cat_resp.status_code == 200, cat_resp.text
    cat_id = cat_resp.json()["id"]

    art_resp = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=admin_headers,
        json={
            "headline": "Test article",
            "slug": f"test-article-{uuid.uuid4().hex[:8]}",
            "excerpt": "excerpt",
            "body": "<p>body</p>",
            "category_id": cat_id,
            "status": ArticleStatus.published,
        },
    )
    assert art_resp.status_code == 200, art_resp.text
    article_id: str = art_resp.json()["id"]
    return article_id


# ---------------------------------------------------------------------------
# Maintenance mode middleware
# ---------------------------------------------------------------------------


def test_maintenance_mode_blocks_public_traffic(
    client: TestClient, db: Session
) -> None:
    """When ``dev_maintenance_mode`` is true, public endpoints must return
    503 with the documented payload."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, True)
    try:
        r = client.post(
            f"{settings.API_V1_STR}/contact/",
            json={
                "name": "Tester",
                "email": "tester@example.com",
                "subject": "hi",
                "message": "hello",
            },
        )
        assert r.status_code == 503
        assert r.json() == {"detail": "Service is in maintenance mode"}

        # Public reads should also be blocked during maintenance.
        r = client.get(f"{settings.API_V1_STR}/articles/")
        assert r.status_code == 503
    finally:
        _reset_all_flags(db)


def test_maintenance_mode_allows_documented_paths(
    client: TestClient, db: Session
) -> None:
    """Auth, developer tooling, health, docs, settings, and uploads must
    remain reachable during a maintenance window."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, True)
    dev_headers = None
    try:
        # Health and developer endpoints stay reachable.
        r = client.get(f"{settings.API_V1_STR}/utils/health-check/")
        assert r.status_code == 200
        r = client.get(f"{settings.API_V1_STR}/settings/")
        assert r.status_code == 200

        dev_headers = _make_developer_headers(client, db)
        r = client.get(
            f"{settings.API_V1_STR}/developer/health", headers=dev_headers
        )
        assert r.status_code == 200
        r = client.get(
            f"{settings.API_V1_STR}/developer/feature-flags", headers=dev_headers
        )
        assert r.status_code == 200

        # Login must still work so the operator can sign in during maintenance.
        email = random_email()
        password = random_lower_string()
        crud.create_user(
            session=db,
            user_create=UserCreate(
                email=email,
                password=password,
                role=UserRole.contributor,
            ),
        )
        r = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": email, "password": password},
        )
        assert r.status_code == 200

        # Docs surfaces remain available. ``openapi_url`` is mounted under
        # ``settings.API_V1_STR`` (see ``backend/app/main.py``); the
        # allowlist mirrors the served path.
        r = client.get(f"{settings.API_V1_STR}/openapi.json")
        assert r.status_code == 200
    finally:
        _reset_all_flags(db)


def test_maintenance_mode_disabled_allows_public_traffic(
    client: TestClient, db: Session
) -> None:
    """When the flag is false (default), public traffic flows normally."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, False)
    try:
        r = client.get(f"{settings.API_V1_STR}/articles/")
        # Public articles list is unauthenticated and must return 200,
        # not 503 from the maintenance middleware.
        assert r.status_code == 200
    finally:
        _reset_all_flags(db)


# ---------------------------------------------------------------------------
# Per-feature flag enforcement deps
# ---------------------------------------------------------------------------


def test_public_comments_blocked_when_flag_disabled(
    client: TestClient, db: Session
) -> None:
    """``dev_public_comments_enabled=false`` must 403 the public POST."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, False)
    _set_flag(db, FLAG_PUBLIC_COMMENTS_ENABLED, False)
    try:
        article_id = _make_article_with_admin(client, db)
        r = client.post(
            f"{settings.API_V1_STR}/comments/",
            json={
                "article_id": article_id,
                "guest_name": "Tester",
                "guest_email": "tester@example.com",
                "body": "hi",
            },
        )
        assert r.status_code == 403
        assert "comments" in r.json()["detail"].lower()
    finally:
        _reset_all_flags(db)


def test_public_comments_admin_endpoints_unaffected_by_flag(
    client: TestClient, db: Session
) -> None:
    """Disabling public comments must not block admin moderation routes."""
    _set_flag(db, FLAG_PUBLIC_COMMENTS_ENABLED, False)
    try:
        admin_headers = _make_admin_headers(client, db)
        r = client.get(
            f"{settings.API_V1_STR}/comments/", headers=admin_headers
        )
        # Admin moderation list must still respond (200).
        assert r.status_code == 200
    finally:
        _reset_all_flags(db)


def test_contact_form_blocked_when_flag_disabled(
    client: TestClient, db: Session
) -> None:
    """``dev_contact_form_enabled=false`` must 403 the public POST."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, False)
    _set_flag(db, FLAG_CONTACT_FORM_ENABLED, False)
    try:
        r = client.post(
            f"{settings.API_V1_STR}/contact/",
            json={
                "name": "Tester",
                "email": "tester@example.com",
                "subject": "hi",
                "message": "hello",
            },
        )
        assert r.status_code == 403
        assert "contact" in r.json()["detail"].lower()
    finally:
        _reset_all_flags(db)


def test_contact_form_admin_inbox_unaffected_by_flag(
    client: TestClient, db: Session
) -> None:
    """Disabling public contact form must not block the admin inbox."""
    _set_flag(db, FLAG_CONTACT_FORM_ENABLED, False)
    try:
        admin_headers = _make_admin_headers(client, db)
        r = client.get(
            f"{settings.API_V1_STR}/contact/", headers=admin_headers
        )
        assert r.status_code == 200
    finally:
        _reset_all_flags(db)


def test_public_signup_blocked_when_flag_disabled(
    client: TestClient, db: Session
) -> None:
    """``dev_allow_public_signup=false`` must 403 the public signup."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, False)
    _set_flag(db, FLAG_ALLOW_PUBLIC_SIGNUP, False)
    try:
        r = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json={
                "email": random_email(),
                "password": random_lower_string(),
                "full_name": "Blocked",
            },
        )
        assert r.status_code == 403
        assert "sign" in r.json()["detail"].lower()
    finally:
        _reset_all_flags(db)


def test_public_signup_admin_provisioning_unaffected_by_flag(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Disabling public signup must not stop Super Admin from creating
    users via the admin endpoint."""
    _set_flag(db, FLAG_ALLOW_PUBLIC_SIGNUP, False)
    try:
        r = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json={
                "email": random_email(),
                "password": random_lower_string(),
                "is_developer": False,
            },
        )
        assert r.status_code == 200
    finally:
        _reset_all_flags(db)


def test_developer_endpoints_still_require_developer_role(
    client: TestClient, db: Session
) -> None:
    """Flag state must not weaken the developer RBAC: a non-developer
    must still be 403 on ``/developer/*``."""
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            password=password,
            role=UserRole.contributor,
            is_developer=False,
        ),
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)
    r = client.get(
        f"{settings.API_V1_STR}/developer/health", headers=headers
    )
    assert r.status_code == 403


def test_flag_value_not_overridable_via_query_param(
    client: TestClient, db: Session
) -> None:
    """The flag value must be authoritative; clients cannot disable an
    enforcement dep via query parameter or header."""
    _set_flag(db, FLAG_MAINTENANCE_MODE, False)
    _set_flag(db, FLAG_PUBLIC_COMMENTS_ENABLED, False)
    try:
        article_id = _make_article_with_admin(client, db)
        # Try a handful of common bypass payloads: query string, header.
        r = client.post(
            f"{settings.API_V1_STR}/comments/?public_comments_enabled=true",
            json={
                "article_id": article_id,
                "guest_name": "Tester",
                "guest_email": "tester@example.com",
                "body": "hi",
            },
        )
        assert r.status_code == 403
        r = client.post(
            f"{settings.API_V1_STR}/comments/",
            headers={"X-Force-Flag": "1"},
            json={
                "article_id": article_id,
                "guest_name": "Tester",
                "guest_email": "tester@example.com",
                "body": "hi",
            },
        )
        assert r.status_code == 403
    finally:
        _reset_all_flags(db)
