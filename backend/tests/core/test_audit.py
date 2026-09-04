from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.audit import redact_sensitive, write_audit_log
from app.core.config import settings
from app.models import AuditLog, UserCreate, UserRole
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def _audit_by_event(db: Session, event: str, *, limit: int = 100) -> list[AuditLog]:
    rows = db.exec(
        select(AuditLog)
        .where(AuditLog.event == event)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    ).all()
    return list(rows)


def test_redact_sensitive_removes_secrets_and_nested_credentials() -> None:
    payload = {
        "email": "user@example.com",
        "password": "super-secret",
        "access_token": "abc.def.ghi",
        "authorization": "Bearer xyz",
        "nested": {"api_key": "k-123", "token": "t-456", "ok": 1},
        "client_secret": "cs",
        "database_url": "postgres://u:p@host/db",
    }
    redacted = redact_sensitive(payload)
    assert redacted is not None
    assert redacted["password"] == "[REDACTED]"
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["client_secret"] == "[REDACTED]"
    assert redacted["database_url"] == "[REDACTED]"
    assert redacted["email"] == "user@example.com"
    assert redacted["nested"]["ok"] == 1


def test_write_audit_log_persists_redacted_event(db: Session) -> None:
    write_audit_log(
        session=db,
        event="system.test",
        component="test",
        severity="WARN",
        message="used token dangling",
        target_type="article",
        target_id="00000000-0000-0000-0000-000000000000",
        success=True,
    )
    db.commit()
    rows = _audit_by_event(db, "system.test")
    assert len(rows) >= 1
    entry = rows[0]
    assert entry.component == "test"
    assert entry.severity == "WARN"
    assert entry.event == "system.test"


def test_login_success_and_failure_create_audit_events(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.contributor
        ),
    )

    # Failed login (wrong password) -> auth.login_failed, success=False
    r_fail = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": "wrong-password"},
    )
    assert r_fail.status_code == 400
    fails = _audit_by_event(db, "auth.login_failed")
    assert any(not e.success for e in fails)

    # Successful login -> auth.login, success=True
    headers = user_authentication_headers(client=client, email=email, password=password)
    assert headers["Authorization"]
    successes = _audit_by_event(db, "auth.login")
    assert any(e.event == "auth.login" and e.success for e in successes)


def test_developer_logs_return_real_events_and_ordering(
    client: TestClient, db: Session
) -> None:
    dev_email = random_email()
    dev_password = random_lower_string()
    dev_user_in = UserCreate(
        email=dev_email,
        password=dev_password,
        role=UserRole.contributor,
        is_developer=True,
    )
    crud.create_user(session=db, user_create=dev_user_in)
    dev_headers = user_authentication_headers(
        client=client, email=dev_email, password=dev_password
    )

    # Generate a distinct audit event by updating a feature flag.
    r_patch = client.patch(
        f"{settings.API_V1_STR}/developer/feature-flags",
        headers=dev_headers,
        json={"maintenance_mode": True, "public_comments_enabled": False},
    )
    assert r_patch.status_code == 200
    client.patch(
        f"{settings.API_V1_STR}/developer/feature-flags",
        headers=dev_headers,
        json={"maintenance_mode": False, "public_comments_enabled": True},
    )

    r_logs = client.get(f"{settings.API_V1_STR}/developer/logs", headers=dev_headers)
    assert r_logs.status_code == 200
    logs_data = r_logs.json()
    assert logs_data["count"] > 0
    events = [entry["event"] for entry in logs_data["data"] if entry.get("event")]
    assert "developer.feature_flags_updated" in events

    # Entries are ordered newest-first by created_at.
    timestamps = [entry["timestamp"] for entry in logs_data["data"]]
    assert timestamps == sorted(timestamps, reverse=True)

    # Every entry preserves the frontend contract fields.
    for entry in logs_data["data"]:
        assert "id" in entry
        assert "timestamp" in entry
        assert "level" in entry
        assert "component" in entry
        assert "message" in entry


def test_user_role_and_developer_change_generate_audit_events(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    r_signup = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": email, "password": password, "full_name": "Someone"},
    )
    assert r_signup.status_code == 200
    user_id = r_signup.json()["id"]
    created_rows = _audit_by_event(db, "user.created")
    assert any(e.target_id == user_id for e in created_rows)

    # Grant developer access -> user.developer_access_granted
    r_grant = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json={"is_developer": True},
    )
    assert r_grant.status_code == 200
    granted = _audit_by_event(db, "user.developer_access_granted")
    assert any(e.target_id == user_id for e in granted)
