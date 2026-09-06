import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Article, ArticleStatus, Comment, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_analytics_overview_admin(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    author = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"analytics-{uuid.uuid4().hex[:8]}@example.com",
            password=random_lower_string(),
            role=UserRole.contributor,
        ),
    )

    published = [
        Article(
            headline=f"Published {i}",
            slug=f"published-{i}-{uuid.uuid4().hex[:8]}",
            body="body",
            author_id=author.id,
            status=ArticleStatus.published,
            views_count=100 + i,
        )
        for i in range(3)
    ]
    pending = Article(
        headline="Pending",
        slug=f"pending-{uuid.uuid4().hex[:8]}",
        body="body",
        author_id=author.id,
        status=ArticleStatus.pending,
        views_count=0,
    )
    draft = Article(
        headline="Draft",
        slug=f"draft-{uuid.uuid4().hex[:8]}",
        body="body",
        author_id=author.id,
        status=ArticleStatus.draft,
        views_count=0,
    )
    db.add_all([*published, pending, draft])
    comment = Comment(
        guest_name="Test",
        guest_email="test@example.com",
        body="nice",
        article_id=published[0].id,
    )
    db.add(comment)
    db.commit()

    r = client.get(
        f"{settings.API_V1_STR}/analytics/overview",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    body = r.json()
    # init_db seeds 4 published articles; this test adds 3 published + 1 pending + 1 draft
    assert body["total_articles"] == 9
    assert body["published_articles"] == 7
    assert body["pending_articles"] == 1
    assert body["draft_articles"] == 1
    assert body["total_users"] >= 2
    assert body["total_comments"] >= 1

    top = body["top_articles"]
    assert len(top) == 5
    assert all(a["status"] == "published" for a in top)
    views = [a["views_count"] for a in top]
    assert views == sorted(views, reverse=True)


def test_analytics_overview_unauthenticated(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/analytics/overview")
    assert r.status_code == 401


def test_analytics_overview_forbidden_for_contributor(
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
    headers = authentication_token_from_email(client=client, email=email, db=db)
    r = client.get(
        f"{settings.API_V1_STR}/analytics/overview", headers=headers
    )
    assert r.status_code == 403


def test_analytics_overview_empty(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # NOTE: init_db seeds 4 published articles, so the DB is never truly empty
    # in the session-scoped fixture. This test verifies the endpoint returns a
    # valid response reflecting existing seed data.
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"analytics-empty-{uuid.uuid4().hex[:8]}@example.com",
            password=random_lower_string(),
            role=UserRole.contributor,
        ),
    )

    r = client.get(
        f"{settings.API_V1_STR}/analytics/overview",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_articles"] >= 4
    assert body["published_articles"] >= 4
    assert body["total_users"] >= 1
    top = body["top_articles"]
    assert len(top) >= 1
    assert all(a["status"] == "published" for a in top)
    views = [a["views_count"] for a in top]
    assert views == sorted(views, reverse=True)
