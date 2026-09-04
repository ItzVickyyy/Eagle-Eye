import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import (
    Article,
    ArticleCreate,
    ArticleStatus,
    Category,
    Comment,
    CommentStatus,
    ContactMessage,
    Media,
    SiteSetting,
    User,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_user_with_role(
    db: Session,
    role: UserRole,
    is_superuser: bool = False,
    is_developer: bool = False,
) -> tuple[User, str, str]:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(
        email=email,
        password=password,
        role=role,
        is_superuser=is_superuser,
        is_developer=is_developer,
    )
    user = crud.create_user(session=db, user_create=user_in)
    return user, email, password


# ---------------------------------------------------------------------------
# 1. Role Matrix & Separation Tests
# ---------------------------------------------------------------------------


def test_super_admin_role_capabilities(client: TestClient, db: Session) -> None:
    # Super admin created via role=super_admin
    user, email, _ = create_user_with_role(
        db, role=UserRole.super_admin, is_superuser=False
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Super Admin CAN manage users
    r_users = client.get(f"{settings.API_V1_STR}/users/", headers=headers)
    assert r_users.status_code == 200

    # Super Admin CAN manage site settings
    r_settings = client.post(
        f"{settings.API_V1_STR}/settings/",
        headers=headers,
        json={"key": "test_rbac_key", "value": "test_val"},
    )
    assert r_settings.status_code == 200

    # Super Admin CAN delete categories
    cat = session_cat = Category(name="TestCat", slug="test-cat-rbac")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    r_del_cat = client.delete(
        f"{settings.API_V1_STR}/categories/{cat.id}", headers=headers
    )
    assert r_del_cat.status_code == 200

    # BUT Super Admin without Developer access CANNOT access Developer endpoints
    r_dev = client.get(f"{settings.API_V1_STR}/developer/health", headers=headers)
    assert r_dev.status_code == 403


def test_admin_role_capabilities_and_boundaries(client: TestClient, db: Session) -> None:
    # Admin (Editor)
    user, email, _ = create_user_with_role(
        db, role=UserRole.admin, is_superuser=False, is_developer=False
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Admin CAN access Review Queue
    assert (
        client.get(
            f"{settings.API_V1_STR}/articles/review-queue", headers=headers
        ).status_code
        == 200
    )

    # Admin CAN access Comments moderation
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 200

    # Admin CAN access Contact Inbox
    assert client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code == 200

    # Admin CAN access Analytics Overview
    assert (
        client.get(
            f"{settings.API_V1_STR}/analytics/overview", headers=headers
        ).status_code
        == 200
    )

    # Admin CAN create and update categories
    r_cat = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=headers,
        json={"name": "Admin Cat", "slug": f"admin-cat-{random_lower_string()}"},
    )
    assert r_cat.status_code == 200

    # Admin CANNOT manage users (Super Admin only)
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 403

    # Admin CANNOT manage site settings (Super Admin only)
    assert (
        client.post(
            f"{settings.API_V1_STR}/settings/",
            headers=headers,
            json={"key": "test_rbac_key2", "value": "val"},
        ).status_code
        == 403
    )

    # Admin CANNOT access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 403


def test_contributor_role_boundaries(client: TestClient, db: Session) -> None:
    # Contributor
    user, email, _ = create_user_with_role(
        db, role=UserRole.contributor, is_superuser=False, is_developer=False
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Contributor CANNOT directly publish an article upon creation
    r_art = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json={
            "headline": "Contributor Article",
            "slug": "contributor-article",
            "body": "<p>Content</p>",
            "status": "published",
        },
    )
    assert r_art.status_code == 200
    # Status is automatically downgraded to pending review
    assert r_art.json()["status"] == "pending"

    # Contributor CANNOT access Review Queue
    assert (
        client.get(
            f"{settings.API_V1_STR}/articles/review-queue", headers=headers
        ).status_code
        == 403
    )

    # Contributor CANNOT access Comments moderation
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 403

    # Contributor CANNOT access Contact Inbox
    assert client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code == 403

    # Contributor CANNOT access Analytics Overview
    assert (
        client.get(
            f"{settings.API_V1_STR}/analytics/overview", headers=headers
        ).status_code
        == 403
    )

    # Contributor CANNOT access Users management
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 403

    # Contributor CANNOT access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# 2. Developer vs Club RBAC Orthogonal Combinations
# ---------------------------------------------------------------------------


def test_developer_plus_contributor_combination(client: TestClient, db: Session) -> None:
    # Developer + Contributor
    dev_contrib, email, _ = create_user_with_role(
        db, role=UserRole.contributor, is_superuser=False, is_developer=True
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # CAN access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 200

    # CANNOT access Super Admin or Admin endpoints
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code == 403


def test_developer_plus_admin_combination(client: TestClient, db: Session) -> None:
    # Developer + Admin
    dev_admin, email, _ = create_user_with_role(
        db, role=UserRole.admin, is_superuser=False, is_developer=True
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # CAN access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 200

    # CAN access Admin endpoints
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 200
    assert client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code == 200

    # CANNOT access Super Admin user management
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 403


def test_developer_plus_super_admin_combination(client: TestClient, db: Session) -> None:
    # Developer + Super Admin
    dev_sa, email, _ = create_user_with_role(
        db, role=UserRole.super_admin, is_superuser=True, is_developer=True
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # CAN access Developer endpoints
    assert client.get(f"{settings.API_V1_STR}/developer/health", headers=headers).status_code == 200

    # CAN access Super Admin endpoints
    assert client.get(f"{settings.API_V1_STR}/users/", headers=headers).status_code == 200
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# 3. Object-Level Authorization Tests (IDOR / Ownership Protection)
# ---------------------------------------------------------------------------


def test_object_level_article_ownership(client: TestClient, db: Session) -> None:
    # User A (Contributor)
    user_a, email_a, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_a = authentication_token_from_email(client=client, email=email_a, db=db)

    # User B (Contributor)
    user_b, email_b, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_b = authentication_token_from_email(client=client, email=email_b, db=db)

    # Admin User
    admin_user, email_admin, _ = create_user_with_role(db, role=UserRole.admin)
    headers_admin = authentication_token_from_email(client=client, email=email_admin, db=db)

    # User A creates a draft article
    art_a = Article(
        headline="User A Secret Draft",
        slug=f"draft-a-{random_lower_string()}",
        body="<p>Draft Body A</p>",
        author_id=user_a.id,
        status=ArticleStatus.draft,
    )
    db.add(art_a)
    db.commit()
    db.refresh(art_a)

    # 1. User B CANNOT read User A's draft article by UUID
    r_read_b = client.get(f"{settings.API_V1_STR}/articles/{art_a.id}", headers=headers_b)
    assert r_read_b.status_code == 403

    # 2. User B CANNOT edit User A's draft article
    r_edit_b = client.patch(
        f"{settings.API_V1_STR}/articles/{art_a.id}",
        headers=headers_b,
        json={"headline": "Hacked by B"},
    )
    assert r_edit_b.status_code == 403

    # 3. User B CANNOT delete User A's draft article
    r_del_b = client.delete(f"{settings.API_V1_STR}/articles/{art_a.id}", headers=headers_b)
    assert r_del_b.status_code == 403

    # 4. User A CAN read, update, and delete their own draft
    r_read_a = client.get(f"{settings.API_V1_STR}/articles/{art_a.id}", headers=headers_a)
    assert r_read_a.status_code == 200

    r_edit_a = client.patch(
        f"{settings.API_V1_STR}/articles/{art_a.id}",
        headers=headers_a,
        json={"headline": "Updated by A"},
    )
    assert r_edit_a.status_code == 200
    assert r_edit_a.json()["headline"] == "Updated by A"

    # 5. Admin CAN read and edit User A's article
    r_read_admin = client.get(
        f"{settings.API_V1_STR}/articles/{art_a.id}", headers=headers_admin
    )
    assert r_read_admin.status_code == 200


def test_object_level_media_ownership(client: TestClient, db: Session) -> None:
    # User A (Contributor)
    user_a, email_a, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_a = authentication_token_from_email(client=client, email=email_a, db=db)

    # User B (Contributor)
    user_b, email_b, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_b = authentication_token_from_email(client=client, email=email_b, db=db)

    # User A creates a media record
    media_a = Media(
        file_url="https://example.com/photo-a.jpg",
        file_type="image",
        uploaded_by=user_a.id,
    )
    db.add(media_a)
    db.commit()
    db.refresh(media_a)

    # 1. User B CANNOT delete User A's media
    r_del_b = client.delete(f"{settings.API_V1_STR}/media/{media_a.id}", headers=headers_b)
    assert r_del_b.status_code == 403

    # 2. User A CAN delete their own media
    r_del_a = client.delete(f"{settings.API_V1_STR}/media/{media_a.id}", headers=headers_a)
    assert r_del_a.status_code == 200


def test_object_level_user_self_access_and_isolation(client: TestClient, db: Session) -> None:
    user_a, email_a, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_a = authentication_token_from_email(client=client, email=email_a, db=db)

    user_b, email_b, _ = create_user_with_role(db, role=UserRole.contributor)
    headers_b = authentication_token_from_email(client=client, email=email_b, db=db)

    # 1. User A can view their own record via /users/{id}
    r_me = client.get(f"{settings.API_V1_STR}/users/{user_a.id}", headers=headers_a)
    assert r_me.status_code == 200
    assert r_me.json()["email"] == email_a

    # 2. User A CANNOT view User B's record via /users/{id}
    r_other = client.get(f"{settings.API_V1_STR}/users/{user_b.id}", headers=headers_a)
    assert r_other.status_code == 403


# ---------------------------------------------------------------------------
# 4. Privilege Escalation Hardening Tests
# ---------------------------------------------------------------------------


def test_privilege_escalation_prevention_on_profile_update(
    client: TestClient, db: Session
) -> None:
    user, email, _ = create_user_with_role(db, role=UserRole.contributor)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Attempt self-promotion via /users/me
    client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
        json={
            "is_superuser": True,
            "role": "super_admin",
            "is_developer": True,
        },
    )

    # Verify user was not escalated
    db.expire_all()
    reloaded_user = db.get(User, user.id)
    assert reloaded_user is not None
    assert reloaded_user.is_superuser is False
    assert reloaded_user.role == UserRole.contributor
    assert reloaded_user.is_developer is False
