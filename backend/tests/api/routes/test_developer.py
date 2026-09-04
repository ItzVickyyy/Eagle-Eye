from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate, UserRole, UserUpdate
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


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
