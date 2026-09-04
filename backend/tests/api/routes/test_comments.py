import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Article,
    Comment,
    CommentStatus,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_public_create_and_read_article_comments(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
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

    # 2. Public creates comment
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
    assert comment["status"] == "approved"
    assert "id" in comment

    # 3. Read article comments (public)
    read_res = client.get(f"{settings.API_V1_STR}/comments/article/{art_id}")
    assert read_res.status_code == 200
    res_data = read_res.json()
    assert res_data["count"] >= 1
    assert any(c["id"] == comment["id"] for c in res_data["data"])


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
