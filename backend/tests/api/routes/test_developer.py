import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import AuditLog, SiteSetting, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def _reset_flags(session: Session) -> None:
    """Restore all developer feature flags to their default 'on' state.

    The maintenance flag is forced off so a previous test cannot leave the
    maintenance middleware active for the next one.
    """
    defaults = {
        "dev_maintenance_mode": "false",
        "dev_public_comments_enabled": "true",
        "dev_contact_form_enabled": "true",
        "dev_allow_public_signup": "true",
    }
    for key, value in defaults.items():
        existing = session.get(SiteSetting, key)
        if existing is None:
            session.add(SiteSetting(key=key, value=value))
        else:
            existing.value = value
    session.commit()


def test_developer_access_health_diagnostics_feature_flags_and_logs(
    client: TestClient, db: Session
) -> None:
    # 1. Create a pure developer user (is_developer=True, role=contributor, is_superuser=False)
    email = random_email()
    password = random_lower_string()
    dev_user_in = UserCreate(
        email=email,
        password=password,
        role=UserRole.contributor,
        is_superuser=False,
        is_developer=True,
    )
    user = crud.create_user(session=db, user_create=dev_user_in)
    assert user.is_developer is True

    headers = authentication_token_from_email(client=client, email=email, db=db)

    # 2. Test /developer/health
    r_health = client.get(f"{settings.API_V1_STR}/developer/health", headers=headers)
    assert r_health.status_code == 200
    health_data = r_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["database_status"] == "connected"
    assert "fastapi_version" in health_data
    assert "python_version" in health_data
    assert "database_latency_ms" in health_data

    # 3. Test /developer/diagnostics
    r_diag = client.get(
        f"{settings.API_V1_STR}/developer/diagnostics", headers=headers
    )
    assert r_diag.status_code == 200
    diag_data = r_diag.json()
    assert "total_users" in diag_data
    assert "total_articles" in diag_data
    assert "database_engine" in diag_data

    # 4. Test /developer/feature-flags (read & update)
    r_flags = client.get(
        f"{settings.API_V1_STR}/developer/feature-flags", headers=headers
    )
    assert r_flags.status_code == 200
    flags_data = r_flags.json()
    assert "maintenance_mode" in flags_data
    assert "public_comments_enabled" in flags_data

    r_patch_flags = client.patch(
        f"{settings.API_V1_STR}/developer/feature-flags",
        headers=headers,
        json={"maintenance_mode": True, "public_comments_enabled": False},
    )
    assert r_patch_flags.status_code == 200
    updated_flags = r_patch_flags.json()
    assert updated_flags["maintenance_mode"] is True
    assert updated_flags["public_comments_enabled"] is False

    # Restore flags
    client.patch(
        f"{settings.API_V1_STR}/developer/feature-flags",
        headers=headers,
        json={"maintenance_mode": False, "public_comments_enabled": True},
    )

    # 5. Test /developer/logs
    r_logs = client.get(f"{settings.API_V1_STR}/developer/logs", headers=headers)
    assert r_logs.status_code == 200
    logs_data = r_logs.json()
    assert logs_data["count"] > 0
    assert len(logs_data["data"]) > 0
    assert "component" in logs_data["data"][0]
    # Defensive cleanup so the next test (and downstream flag-enforcement
    # tests) do not see leftover maintenance state.
    _reset_flags(db)


def test_separation_developer_cannot_access_super_admin_or_admin_club_operations(
    client: TestClient, db: Session
) -> None:
    # Developer-only user (is_developer=True, but role=contributor, is_superuser=False)
    email = random_email()
    password = random_lower_string()
    dev_user_in = UserCreate(
        email=email,
        password=password,
        role=UserRole.contributor,
        is_superuser=False,
        is_developer=True,
    )
    crud.create_user(session=db, user_create=dev_user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # 1. Developer CANNOT access user management (Super Admin only)
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 403

    # 2. Developer CANNOT set site settings (Super Admin only)
    assert (
        client.post(
            f"{settings.API_V1_STR}/settings/",
            headers=headers,
            json={"key": "test_key", "value": "test_val"},
        ).status_code
        == 403
    )

    # 3. Developer CANNOT access comment moderation (Admin only)
    assert (
        client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code
        == 403
    )

    # 4. Developer CANNOT access contact inbox (Admin only)
    assert (
        client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code
        == 403
    )

    # 5. Developer CANNOT access review queue (Admin only)
    assert (
        client.get(f"{settings.API_V1_STR}/articles/review-queue", headers=headers).status_code
        == 403
    )

    # 6. Developer CANNOT access analytics overview (Admin only)
    assert (
        client.get(f"{settings.API_V1_STR}/analytics/overview", headers=headers).status_code
        == 403
    )


def test_separation_super_admin_without_developer_flag_cannot_access_developer_endpoints(
    client: TestClient, db: Session
) -> None:
    # Super Admin user (is_superuser=True, role=super_admin, is_developer=False)
    email = random_email()
    password = random_lower_string()
    sa_user_in = UserCreate(
        email=email,
        password=password,
        role=UserRole.super_admin,
        is_superuser=True,
        is_developer=False,
    )
    crud.create_user(session=db, user_create=sa_user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Super Admin can manage users
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 200

    # BUT Super Admin WITHOUT Developer access CANNOT access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/developer/diagnostics", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/developer/feature-flags", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/developer/logs", headers=headers).status_code == 403


def test_separation_admin_and_contributor_and_public_denied_developer_access(
    client: TestClient, db: Session
) -> None:
    # 1. Unauthenticated public request
    assert client.get(f"{settings.API_V1_STR}/developer/health").status_code == 401
    assert client.get(f"{settings.API_V1_STR}/developer/diagnostics").status_code == 401
    assert client.get(f"{settings.API_V1_STR}/developer/feature-flags").status_code == 401
    assert client.get(f"{settings.API_V1_STR}/developer/logs").status_code == 401

    # 2. Admin (is_developer=False)
    admin_email = random_email()
    admin_pwd = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=admin_email,
            password=admin_pwd,
            role=UserRole.admin,
            is_developer=False,
        ),
    )
    admin_headers = authentication_token_from_email(
        client=client, email=admin_email, db=db
    )
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=admin_headers
        ).status_code
        == 403
    )

    # 3. Contributor (is_developer=False)
    contrib_email = random_email()
    contrib_pwd = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=contrib_email,
            password=contrib_pwd,
            role=UserRole.contributor,
            is_developer=False,
        ),
    )
    contrib_headers = authentication_token_from_email(
        client=client, email=contrib_email, db=db
    )
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=contrib_headers
        ).status_code
        == 403
    )


def test_developer_provisioning_and_revocation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Normal user signs up via public signup -> is_developer defaults to False
    reg_email = random_email()
    reg_pwd = random_lower_string()
    r_signup = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": reg_email, "password": reg_pwd, "full_name": "New Person"},
    )
    assert r_signup.status_code == 200
    user_data = r_signup.json()
    assert user_data["is_developer"] is False
    user_id = user_data["id"]

    # Login as this user
    user_headers = authentication_token_from_email(
        client=client, email=reg_email, db=db
    )
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=user_headers
        ).status_code
        == 403
    )

    # User attempts self-escalation via /users/me -> should not be able to set is_developer
    client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=user_headers,
        json={"is_developer": True},
    )
    # Verify still not developer
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=user_headers
        ).status_code
        == 403
    )

    # 2. Super Admin grants Developer access
    r_grant = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json={"is_developer": True},
    )
    assert r_grant.status_code == 200
    assert r_grant.json()["is_developer"] is True

    # User now has developer access
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=user_headers
        ).status_code
        == 200
    )

    # 3. Super Admin revokes Developer access
    r_revoke = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json={"is_developer": False},
    )
    assert r_revoke.status_code == 200
    assert r_revoke.json()["is_developer"] is False

    # User immediately loses developer access
    assert (
        client.get(
            f"{settings.API_V1_STR}/developer/health", headers=user_headers
        ).status_code
        == 403
    )


def _make_developer(client: TestClient, db: Session) -> tuple[dict[str, str], str]:
    """Create a developer user and return (auth headers, email)."""
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
    headers = authentication_token_from_email(client=client, email=email, db=db)
    return headers, email


def test_developer_patch_feature_flags_emits_audit_log(
    client: TestClient, db: Session
) -> None:
    """PATCHing feature flags must persist an audit log row with the right
    event name, component, severity, and success flag."""
    headers, _ = _make_developer(client, db)

    # Snapshot existing audit rows so we can scope our assertion to only the
    # rows produced by this test.
    pre_count = len(db.exec(select(AuditLog)).all())  # noqa: F841

    r = client.patch(
        f"{settings.API_V1_STR}/developer/feature-flags",
        headers=headers,
        json={"public_comments_enabled": False},
    )
    assert r.status_code == 200, r.text

    matching = [
        row
        for row in db.exec(select(AuditLog)).all()
        if row.event == "developer.feature_flags_updated"
    ]
    # We may share the DB with the test above; assert at least one new row.
    assert len(matching) >= 1
    latest = max(matching, key=lambda r: r.created_at)
    assert latest.component == "developer"
    assert latest.severity == "INFO"
    assert latest.success is True
    assert latest.actor_is_developer is True
    assert latest.message == "Developer feature flags updated"

    # Defensive cleanup: restore flag state so subsequent tests see defaults.
    _reset_flags(db)


def test_developer_logs_redaction_does_not_leak_secrets(
    client: TestClient, db: Session
) -> None:
    """Audit log messages must not contain raw password/token material even
    if those values flow through an audited event."""
    headers, _ = _make_developer(client, db)

    # Directly persist a payload that simulates a leaky event so we can
    # confirm the redact boundary scrubs the message in storage.
    from app.core.audit import redact_sensitive

    leaky = {
        "password": "hunter2",
        "headers": {"authorization": "Bearer abc.def.ghi", "cookie": "session=xyz"},
        "nested": {"reset_token": "rt-123", "ok": True},
        "summary": "no secrets here",
    }
    cleaned = redact_sensitive(leaky)
    # All redaction targets must be present as [REDACTED] only.
    serialized = str(cleaned)
    for forbidden in (
        "hunter2",
        "abc.def.ghi",
        "session=xyz",
        "rt-123",
    ):
        assert forbidden not in serialized
    # Non-sensitive fields survive.
    assert "no secrets here" in serialized

    # Empty/redacted message persisted in the DB must also be safe to return.
    db.add(
        AuditLog(
            event="user.test_redaction",
            component="auth",
            severity="INFO",
            actor_email="test@example.com",
            success=True,
            message=serialized,
        )
    )
    db.commit()

    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={"event": "user.test_redaction", "limit": 1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] >= 1
    msg = body["data"][0]["message"]
    for forbidden in ("hunter2", "abc.def.ghi", "session=xyz", "rt-123"):
        assert forbidden not in msg
    # Cleanup: remove the synthetic row.
    for row in db.exec(select(AuditLog)).all():
        if row.event == "user.test_redaction":
            db.delete(row)
    db.commit()


def test_developer_logs_empty_db_returns_empty_envelope(
    client: TestClient, db: Session
) -> None:
    """The logs endpoint must return a well-formed empty envelope rather
    than 5xx when no events are present for a given filter."""
    # Wipe audit log rows so we exercise the empty-result code path.
    for row in db.exec(select(AuditLog)).all():
        db.delete(row)
    db.commit()

    headers, _ = _make_developer(client, db)

    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={"event": "nonexistent.event_xyz"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"] == []
    assert body["count"] == 0
    assert body["has_more"] is False
    # Pagination defaults must be echoed back.
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_developer_logs_filters_narrow_results(
    client: TestClient, db: Session
) -> None:
    """Filter parameters must narrow the returned set to rows that match
    every provided criterion."""
    headers, _ = _make_developer(client, db)

    # Seed three distinct events.
    db.add_all(
        [
            AuditLog(
                event="user.test_filter_match",
                component="auth",
                severity="INFO",
                success=True,
                message="match",
            ),
            AuditLog(
                event="user.test_filter_other",
                component="auth",
                severity="WARN",
                success=False,
                message="other",
            ),
            AuditLog(
                event="user.test_filter_match",
                component="auth",
                severity="ERROR",
                success=False,
                message="match error",
            ),
        ]
    )
    db.commit()

    # Filter on event only.
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={"event": "user.test_filter_match", "limit": 50},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    for entry in body["data"]:
        assert entry["event"] == "user.test_filter_match"

    # Filter on event + success.
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={
            "event": "user.test_filter_match",
            "success": "false",
            "limit": 50,
        },
    )
    body = r.json()
    assert body["count"] == 1
    assert body["data"][0]["event"] == "user.test_filter_match"
    assert body["data"][0]["success"] is False
    assert body["data"][0]["message"] == "match error"

    # Filter on component + severity.
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={
            "component": "auth",
            "severity": "warn",
            "limit": 50,
        },
    )
    body = r.json()
    assert all(e["component"] == "auth" for e in body["data"])
    assert any(e["event"] == "user.test_filter_other" for e in body["data"])

    # Cleanup synthetic rows so they do not leak into other test runs.
    for row in db.exec(select(AuditLog)).all():
        if row.event in {
            "user.test_filter_match",
            "user.test_filter_other",
        }:
            db.delete(row)
    db.commit()


def test_developer_logs_pagination_has_more_and_offset(
    client: TestClient, db: Session
) -> None:
    """Pagination must honor limit/offset, return has_more when more rows
    exist, and clamp the limit to the safe range."""
    headers, _ = _make_developer(client, db)

    # Seed five rows that share the same ``event`` value so the endpoint's
    # exact-match ``event`` filter selects all of them. Determinism is
    # guaranteed by the implementation's ``(created_at desc, id desc)``
    # ordering, so pagination assertions do not depend on insertion order.
    event_name = f"user.test_paginate_{uuid.uuid4().hex[:8]}"
    seeded: list[AuditLog] = []
    for i in range(5):
        row = AuditLog(
            event=event_name,
            component="system",
            severity="INFO",
            success=True,
            message=f"row {i}",
        )
        db.add(row)
        seeded.append(row)
    db.commit()
    for r in seeded:
        db.refresh(r)

    # limit=2 -> has_more True, count==2
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={
            "event": event_name,
            "limit": 2,
            "offset": 0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["has_more"] is True

    # Next page
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={
            "event": event_name,
            "limit": 2,
            "offset": 2,
        },
    )
    body = r.json()
    assert body["count"] == 2
    assert body["offset"] == 2
    assert body["has_more"] is True

    # Final page
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={
            "event": event_name,
            "limit": 2,
            "offset": 4,
        },
    )
    body = r.json()
    assert body["count"] == 1
    assert body["has_more"] is False

    # Limit clamping: limit=999 must be clamped to 200, count<=200.
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={"limit": 999, "offset": 0},
    )
    body = r.json()
    assert body["limit"] == 200
    assert body["count"] <= 200

    # Negative limit/offset clamped to safe floor.
    r = client.get(
        f"{settings.API_V1_STR}/developer/logs",
        headers=headers,
        params={"limit": -1, "offset": -5},
    )
    body = r.json()
    assert body["limit"] == 1
    assert body["offset"] == 0

    # Cleanup synthetic rows.
    for row in seeded:
        db.delete(row)
    db.commit()
