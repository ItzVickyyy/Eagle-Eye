import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import (
    Comment,
    CommentStatus,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_public_create_comment_is_pending_until_approved(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    # 1. Create published article
    art_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Comment Test Article",
            "slug": f"comment-article-{random_lower_string()}",
            "body": "<p>Article content</p>",
            "status": "published",
        },
    )
    assert art_res.status_code == 200
    art_id = art_res.json()["id"]

    # 2. Public creates comment -> must default to pending
    comment_data = {
        "article_id": art_id,
        "guest_name": "Juan Dela Cruz",
        "guest_email": "juan@example.com",
        "body": "Great article!",
    }
    create_res = client.post(
        f"{settings.API_V1_STR}/comments/",
        json=comment_data,
    )
    assert create_res.status_code == 200
    comment = create_res.json()
    assert comment["guest_name"] == "Juan Dela Cruz"
    assert comment["body"] == "Great article!"
    assert comment["status"] == "pending"
    assert "id" in comment

    # 3. Pending comment must NOT be visible in the public list
    read_res = client.get(f"{settings.API_V1_STR}/comments/article/{art_id}")
    assert read_res.status_code == 200
    res_data = read_res.json()
    assert all(c["id"] != comment["id"] for c in res_data["data"])

    # 4. Admin approves comment
    patch_res = client.patch(
        f"{settings.API_V1_STR}/comments/{comment['id']}",
        headers=superuser_token_headers,
        json={"status": "approved"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "approved"

    # 5. Approved comment is now visible in the public list
    read_res = client.get(f"{settings.API_V1_STR}/comments/article/{art_id}")
    assert read_res.status_code == 200
    res_data = read_res.json()
    assert res_data["count"] >= 1
    assert any(c["id"] == comment["id"] for c in res_data["data"])


def test_comment_on_draft_or_pending_article_rejected(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    for status in ("draft", "pending"):
        art_res = client.post(
            f"{settings.API_V1_STR}/articles/",
            headers=superuser_token_headers,
            json={
                "headline": f"Unpublished {status.title()}",
                "slug": f"unpublished-{status}-{random_lower_string()}",
                "body": "<p>Content</p>",
                "status": status,
            },
        )
        assert art_res.status_code == 200
        art_id = art_res.json()["id"]

        # Public commenting on an unpublished article is rejected with the
        # same generic 404 as a nonexistent article (no info leak).
        create_res = client.post(
            f"{settings.API_V1_STR}/comments/",
            json={
                "article_id": art_id,
                "guest_name": "Sneaky Reader",
                "guest_email": "sneaky@example.com",
                "body": "Let me in!",
            },
        )
        assert create_res.status_code == 404
        assert create_res.json()["detail"] == "Article not found"


def test_comment_on_nonexistent_article_rejected(
    client: TestClient,
) -> None:
    create_res = client.post(
        f"{settings.API_V1_STR}/comments/",
        json={
            "article_id": str(uuid.uuid4()),
            "guest_name": "Ghost User",
            "guest_email": "ghost@example.com",
            "body": "Hello?",
        },
    )
    assert create_res.status_code == 404
    assert create_res.json()["detail"] == "Article not found"


def test_spam_comment_not_visible_publicly(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    # 1. Create published article
    art_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Spam Visibility Story",
            "slug": f"spam-vis-story-{random_lower_string()}",
            "body": "<p>Story content</p>",
            "status": "published",
        },
    )
    assert art_res.status_code == 200
    art_id = art_res.json()["id"]

    # 2. Public creates two comments
    ids = []
    for name in ("First", "Second"):
        create_res = client.post(
            f"{settings.API_V1_STR}/comments/",
            json={
                "article_id": art_id,
                "guest_name": name,
                "guest_email": f"{name.lower()}@example.com",
                "body": f"Comment from {name}",
            },
        )
        assert create_res.status_code == 200
        ids.append(create_res.json()["id"])

    # 3. Moderate: approve first, mark second as spam
    for cid, status in ((ids[0], "approved"), (ids[1], "spam")):
        patch_res = client.patch(
            f"{settings.API_V1_STR}/comments/{cid}",
            headers=superuser_token_headers,
            json={"status": status},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == status

    # 4. Public list shows ONLY the approved comment
    read_res = client.get(f"{settings.API_V1_STR}/comments/article/{art_id}")
    assert read_res.status_code == 200
    res_data = read_res.json()
    public_ids = {c["id"] for c in res_data["data"]}
    assert ids[0] in public_ids
    assert ids[1] not in public_ids


def test_admin_list_and_filter_comments_moderation(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create published article
    art_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Moderation Story",
            "slug": f"mod-story-{random_lower_string()}",
            "body": "<p>Story content</p>",
            "status": "published",
        },
    )
    assert art_res.status_code == 200
    art_id = art_res.json()["id"]

    # 2. Add approved and spam comments
    comment1 = Comment(
        article_id=uuid.UUID(art_id),
        guest_name="Approved User",
        guest_email="appr@example.com",
        body="Positive insight",
        status=CommentStatus.approved,
    )
    comment2 = Comment(
        article_id=uuid.UUID(art_id),
        guest_name="Spammer",
        guest_email="spam@example.com",
        body="Buy cheap stuff now",
        status=CommentStatus.spam,
    )
    db.add(comment1)
    db.add(comment2)
    db.commit()
    db.refresh(comment1)
    db.refresh(comment2)

    # 3. Admin lists all comments
    list_res = client.get(
        f"{settings.API_V1_STR}/comments/",
        headers=superuser_token_headers,
    )
    assert list_res.status_code == 200
    all_comments = list_res.json()["data"]
    c1_match = next((c for c in all_comments if c["id"] == comment1.id), None)
    assert c1_match is not None
    assert c1_match["article_headline"] == "Moderation Story"

    # 4. Filter by status=spam
    spam_res = client.get(
        f"{settings.API_V1_STR}/comments/?status=spam",
        headers=superuser_token_headers,
    )
    assert spam_res.status_code == 200
    spam_comments = spam_res.json()["data"]
    assert any(c["id"] == comment2.id for c in spam_comments)
    assert not any(c["id"] == comment1.id for c in spam_comments)


def test_admin_update_comment_status_and_delete(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create article
    art_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Status Update Story",
            "slug": f"status-story-{random_lower_string()}",
            "body": "<p>Content</p>",
            "status": "published",
        },
    )
    art_id = art_res.json()["id"]

    # 2. Create comment
    c = Comment(
        article_id=uuid.UUID(art_id),
        guest_name="Status Check",
        guest_email="check@example.com",
        body="Needs review",
        status=CommentStatus.pending,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    comment_id = c.id
    assert comment_id is not None

    # 3. Admin updates status to approved
    patch_res = client.patch(
        f"{settings.API_V1_STR}/comments/{comment_id}",
        headers=superuser_token_headers,
        json={"status": "approved"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "approved"

    # 4. Admin deletes comment
    del_res = client.delete(
        f"{settings.API_V1_STR}/comments/{comment_id}",
        headers=superuser_token_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Comment deleted successfully"

    # 5. Verify deleted from DB
    db.expire_all()
    assert db.get(Comment, comment_id) is None


def test_contributor_cannot_access_comment_moderation_endpoints(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.contributor)
    from app import crud
    crud.create_user(session=db, user_create=user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # List all comments
    assert client.get(f"{settings.API_V1_STR}/comments/", headers=headers).status_code == 403

    # Update comment status
    assert client.patch(f"{settings.API_V1_STR}/comments/1", headers=headers, json={"status": "approved"}).status_code == 403

    # Delete comment
    assert client.delete(f"{settings.API_V1_STR}/comments/1", headers=headers).status_code == 403


def test_unauthenticated_cannot_access_comment_moderation_endpoints(
    client: TestClient,
) -> None:
    # List (requires AdminUser) -> 401 without credentials
    assert client.get(f"{settings.API_V1_STR}/comments/").status_code == 401

    # Update status -> 401
    assert client.patch(
        f"{settings.API_V1_STR}/comments/1", json={"status": "approved"}
    ).status_code == 401

    # Delete -> 401
    assert client.delete(f"{settings.API_V1_STR}/comments/1").status_code == 401


def test_admin_can_moderate_comments(
    client: TestClient, db: Session
) -> None:
    from app import crud

    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, role=UserRole.admin),
    )
    admin_headers = authentication_token_from_email(
        client=client, email=email, db=db
    )

    # Admin list succeeds (200)
    list_res = client.get(
        f"{settings.API_V1_STR}/comments/", headers=admin_headers
    )
    assert list_res.status_code == 200

    # Admin PATCH succeeds (not 401/403 = RBAC passed; 200 or 404 are acceptable)
    patch_res = client.patch(
        f"{settings.API_V1_STR}/comments/1",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert patch_res.status_code in (200, 404)

    # Admin DELETE succeeds (not 401/403 = RBAC passed)
    del_res = client.delete(
        f"{settings.API_V1_STR}/comments/1", headers=admin_headers
    )
    assert del_res.status_code in (200, 404)
