import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Article, ArticleStatus, Category, User, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_create_article_as_contributor(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.contributor)
    from app import crud
    user = crud.create_user(session=db, user_create=user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Create category
    cat = session_cat = db.exec(select(Category).where(Category.slug == "news")).first()

    data = {
        "headline": "New Student Council Elected",
        "slug": "new-student-council-elected",
        "excerpt": "The election results are in.",
        "body": "Detailed story about the election...",
        "category_id": cat.id if cat else None,
        "status": "pending",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json=data,
    )
    assert r.status_code == 200
    created = r.json()
    assert created["headline"] == data["headline"]
    assert created["status"] == "pending"
    assert created["author_id"] == str(user.id)


def test_contributor_cannot_publish_directly(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.contributor)
    from app import crud
    crud.create_user(session=db, user_create=user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    data = {
        "headline": "Direct Publish Attempt",
        "slug": "direct-publish-attempt",
        "body": "Body content",
        "status": "published",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json=data,
    )
    assert r.status_code == 200
    created = r.json()
    # Should be coerced to pending for contributor
    assert created["status"] == "pending"


def test_admin_publish_article(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    data = {
        "headline": "Official Admin Announcement",
        "slug": "official-admin-announcement",
        "body": "Announcement text",
        "status": "published",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    created = r.json()
    assert created["status"] == "published"
    assert created["date_published"] is not None


def test_public_articles_list_only_published(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # Create draft article
    draft_data = {
        "headline": "Secret Draft",
        "slug": "secret-draft-hidden",
        "body": "Hidden content",
        "status": "draft",
    }
    client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=draft_data,
    )

    # Public get
    r = client.get(f"{settings.API_V1_STR}/articles/")
    assert r.status_code == 200
    data = r.json()
    slugs = [a["slug"] for a in data["data"]]
    assert "secret-draft-hidden" not in slugs


def test_get_article_by_slug_and_increment_views(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    data = {
        "headline": "View Count Test Article",
        "slug": "view-count-test-article",
        "body": "Body here",
        "status": "published",
    }
    client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=data,
    )

    r1 = client.get(f"{settings.API_V1_STR}/articles/slug/view-count-test-article")
    assert r1.status_code == 200
    assert r1.json()["views_count"] == 1

    r2 = client.get(f"{settings.API_V1_STR}/articles/slug/view-count-test-article")
    assert r2.status_code == 200
    assert r2.json()["views_count"] == 2


def test_create_article_sanitizes_xss_body(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    malicious_body = (
        "<script>alert('XSS')</script>"
        "<p>Safe text with <strong>bold</strong>.</p>"
        "<img src=x onerror=alert(1)>"
        "<a href='javascript:alert(2)'>Click</a>"
    )
    data = {
        "headline": "XSS Sanitization Test Article",
        "slug": "xss-sanitization-test-article",
        "body": malicious_body,
        "status": "published",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    created = r.json()
    assert "<script>" not in created["body"]
    assert "onerror" not in created["body"]
    assert "javascript:" not in created["body"]
    assert "<p>Safe text with <strong>bold</strong>.</p>" in created["body"]

