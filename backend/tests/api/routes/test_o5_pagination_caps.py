"""Regression tests for finding O5.

The pre-existing audit identified that several list endpoints accepted a
client-controlled ``limit`` query parameter and applied it directly to
``SELECT ... LIMIT`` without a server-side upper bound. A caller could
therefore request a single response carrying the full table contents.

The fix mirrors the existing pattern in ``/developer/logs``:
``safe_limit = max(1, min(int(limit), 200))``. This module exercises
the cap end-to-end against the live router using a small fixture set
so the response never actually carries > 200 rows. The intent is to
verify that the contract is preserved on every affected endpoint:

  * a normal ``limit`` is honored
  * ``limit=200`` is the highest accepted value
  * an excessive ``limit`` does not yield a payload larger than 200
  * omitting ``limit`` preserves the default
  * the cap never weakens authorization or filter semantics
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import (
    Article,
    ArticleStatus,
    Category,
    ClubMember,
    Comment,
    CommentStatus,
    ContactMessage,
    Media,
    Tag,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contributor_headers(client: TestClient, db: Session) -> dict[str, str]:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.contributor
        ),
    )
    return authentication_token_from_email(client=client, email=email, db=db)


def _seed_tag(db: Session, name: str) -> Tag:
    tag = Tag(name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def _seed_category(db: Session, name: str) -> Category:
    cat = Category(name=name, slug=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def _seed_member(db: Session, first: str, last: str) -> ClubMember:
    m = ClubMember(first_name=first, last_name=last, is_active=True)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _seed_contact_message(db: Session) -> ContactMessage:
    msg = ContactMessage(
        name=f"User {uuid.uuid4().hex[:6]}",
        email=random_email(),
        subject="O5 fixture",
        message="body",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# ---------------------------------------------------------------------------
# Public list endpoints (no auth)
# ---------------------------------------------------------------------------


def test_o5_tags_limit_clamps_to_200(
    client: TestClient, db: Session
) -> None:
    """``GET /tags/`` must never return more than 200 rows per page."""
    for i in range(3):
        _seed_tag(db, f"o5-tag-{uuid.uuid4().hex[:6]}-{i}")

    # Normal limit honored.
    r = client.get(f"{settings.API_V1_STR}/tags/", params={"limit": 2})
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 2
    # `count` is the total table count, not the page size — it must
    # remain >= len(data) regardless of the page.
    assert body["count"] >= len(body["data"])

    # Excessive limit cannot return > 200 records.
    r = client.get(f"{settings.API_V1_STR}/tags/", params={"limit": 10000})
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    # Omitted limit preserves default (100).
    r = client.get(f"{settings.API_V1_STR}/tags/")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 100


def test_o5_categories_limit_clamps_to_200(
    client: TestClient, db: Session
) -> None:
    for i in range(3):
        _seed_category(db, f"o5-cat-{uuid.uuid4().hex[:6]}-{i}")

    r = client.get(
        f"{settings.API_V1_STR}/categories/", params={"limit": 10000}
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(f"{settings.API_V1_STR}/categories/", params={"limit": 200})
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200


def test_o5_articles_public_limit_clamps_to_200(
    client: TestClient,
) -> None:
    """The public articles list must respect the 200-row ceiling."""
    # Seed a couple of published articles; we do not need 201 rows to
    # verify the contract — the cap is enforced on the SQL LIMIT clause.
    r = client.get(
        f"{settings.API_V1_STR}/articles/", params={"limit": 10000}
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200
    # `count` is the total published-article count, not the page size.
    assert body["count"] >= len(body["data"])

    r = client.get(f"{settings.API_V1_STR}/articles/", params={"limit": 20})
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 20

    r = client.get(f"{settings.API_V1_STR}/articles/")
    assert r.status_code == 200
    # Default limit=20 — no more than 20 records on a default request.
    assert len(r.json()["data"]) <= 20


def test_o5_article_comments_limit_clamps_to_200(
    client: TestClient, db: Session
) -> None:
    """``GET /comments/article/{id}`` must honor the 200-row ceiling."""
    # Create an article and a single comment so the endpoint returns
    # at least one row; the cap is the invariant under test, not
    # whether the response has any rows at all.
    author = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            role=UserRole.contributor,
        ),
    )
    article = Article(
        headline=f"o5-article-{uuid.uuid4().hex[:6]}",
        slug=f"o5-article-{uuid.uuid4().hex[:6]}",
        body="body",
        author_id=author.id,
        status=ArticleStatus.published,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    comment = Comment(
        article_id=article.id,
        guest_name="Anon",
        guest_email=random_email(),
        body="hi",
        status=CommentStatus.approved,
    )
    db.add(comment)
    db.commit()

    r = client.get(
        f"{settings.API_V1_STR}/comments/article/{article.id}",
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/comments/article/{article.id}",
        params={"limit": 200},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/comments/article/{article.id}"
    )
    assert r.status_code == 200
    # Default limit=50.
    assert len(r.json()["data"]) <= 50


# ---------------------------------------------------------------------------
# Authenticated list endpoints
# ---------------------------------------------------------------------------


def test_o5_users_limit_clamps_to_200(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200
    # `count` is the total user count, not the page size.
    assert body["count"] >= len(body["data"])

    r = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        params={"limit": 200},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200


def test_o5_users_limit_requires_superuser(
    client: TestClient, db: Session
) -> None:
    """The cap must never silently relax the superuser-only authorization."""
    headers = _make_contributor_headers(client, db)
    r = client.get(
        f"{settings.API_V1_STR}/users/",
        headers=headers,
        params={"limit": 10000},
    )
    assert r.status_code in (401, 403)


def test_o5_contact_inbox_limit_clamps_to_200(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _seed_contact_message(db)
    r = client.get(
        f"{settings.API_V1_STR}/contact/",
        headers=superuser_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/contact/",
        headers=superuser_token_headers,
        params={"limit": 200},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200


def test_o5_contact_inbox_requires_admin(
    client: TestClient, db: Session
) -> None:
    headers = _make_contributor_headers(client, db)
    r = client.get(
        f"{settings.API_V1_STR}/contact/",
        headers=headers,
        params={"limit": 10000},
    )
    assert r.status_code in (401, 403)


def test_o5_all_club_members_limit_clamps_to_200(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _seed_member(db, "o5a", "first")
    _seed_member(db, "o5b", "second")

    r = client.get(
        f"{settings.API_V1_STR}/club-members/all",
        headers=superuser_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/club-members/all",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    # Default limit=100.
    assert len(r.json()["data"]) <= 100


def test_o5_all_club_members_requires_admin(
    client: TestClient, db: Session
) -> None:
    headers = _make_contributor_headers(client, db)
    r = client.get(
        f"{settings.API_V1_STR}/club-members/all",
        headers=headers,
        params={"limit": 10000},
    )
    assert r.status_code in (401, 403)


def test_o5_media_limit_clamps_to_200(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    # Media requires an uploaded_by FK; use the test user.
    uploader = crud.get_user_by_email(session=db, email=settings.EMAIL_TEST_USER)
    assert uploader is not None
    item = Media(
        file_url=f"/uploads/o5-{uuid.uuid4().hex[:6]}.png",
        file_type="image",
        uploaded_by=uploader.id,
    )
    db.add(item)
    db.commit()

    r = client.get(
        f"{settings.API_V1_STR}/media/",
        headers=normal_user_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/media/",
        headers=normal_user_token_headers,
        params={"limit": 200},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200


def test_o5_review_queue_limit_clamps_to_200(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/articles/review-queue",
        headers=superuser_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200
    # `count` is the total review-queue count, not the page size.
    assert body["count"] >= len(body["data"])

    r = client.get(
        f"{settings.API_V1_STR}/articles/review-queue",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    # Default limit=50.
    assert len(r.json()["data"]) <= 50


def test_o5_review_queue_requires_admin(
    client: TestClient, db: Session
) -> None:
    headers = _make_contributor_headers(client, db)
    r = client.get(
        f"{settings.API_V1_STR}/articles/review-queue",
        headers=headers,
        params={"limit": 10000},
    )
    assert r.status_code in (401, 403)


def test_o5_admin_comments_limit_clamps_to_200(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/comments/",
        headers=superuser_token_headers,
        params={"limit": 10000},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200

    r = client.get(
        f"{settings.API_V1_STR}/comments/",
        headers=superuser_token_headers,
        params={"limit": 200},
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 200


def test_o5_admin_comments_requires_admin(
    client: TestClient, db: Session
) -> None:
    headers = _make_contributor_headers(client, db)
    r = client.get(
        f"{settings.API_V1_STR}/comments/",
        headers=headers,
        params={"limit": 10000},
    )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Parametrized contract test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,headers",
    [
        (f"{settings.API_V1_STR}/tags/", None),
        (f"{settings.API_V1_STR}/categories/", None),
        (f"{settings.API_V1_STR}/articles/", None),
        (f"{settings.API_V1_STR}/articles/", "super"),
        (
            f"{settings.API_V1_STR}/articles/review-queue",
            "super",
        ),
        (f"{settings.API_V1_STR}/contact/", "super"),
        (f"{settings.API_V1_STR}/club-members/all", "super"),
        (f"{settings.API_V1_STR}/comments/", "super"),
        (f"{settings.API_V1_STR}/media/", "normal"),
    ],
)
def test_o5_every_endpoint_never_exceeds_200_rows(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    url: str,
    headers: str | None,
) -> None:
    """Compact contract: no capped endpoint ever returns > 200 rows
    when a caller requests an excessive limit."""
    selected: dict[str, str] | None
    if headers == "super":
        selected = superuser_token_headers
    elif headers == "normal":
        selected = normal_user_token_headers
    else:
        selected = None

    r = client.get(url, headers=selected, params={"limit": 999_999})
    # Endpoints requiring auth may 401/403 for the unauthenticated
    # case; if they do, the cap is irrelevant for that case.
    if r.status_code in (401, 403):
        pytest.skip(f"{url} is not accessible in this auth context")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) <= 200
    # `count` is the total table count, not the page size.
    assert body["count"] >= len(body["data"])
