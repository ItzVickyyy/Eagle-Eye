import uuid
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Article,
    ArticleTag,
    Category,
    Tag,
    UserCreate,
    UserRole,
)
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
    cat = db.exec(select(Category).where(Category.slug == "news")).first()

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
    client: TestClient, superuser_token_headers: dict[str, str]
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
    client: TestClient, superuser_token_headers: dict[str, str]
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
    client: TestClient, superuser_token_headers: dict[str, str]
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
    client: TestClient, superuser_token_headers: dict[str, str]
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


def test_create_article_with_multiple_tags_persists_associations(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create tags
    tag1_name = f"Tag-{random_lower_string()}"
    tag2_name = f"Tag-{random_lower_string()}"
    tag1 = Tag(name=tag1_name)
    tag2 = Tag(name=tag2_name)
    db.add(tag1)
    db.add(tag2)
    db.commit()
    db.refresh(tag1)
    db.refresh(tag2)

    # 2. Create article with tags
    slug = f"tag-test-{random_lower_string()}"
    data = {
        "headline": "Article With Tags",
        "slug": slug,
        "body": "Article content with tags",
        "status": "published",
        "tag_ids": [tag1.id, tag2.id],
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    art_id = uuid.UUID(r.json()["id"])

    # 3. Verify ArticleTag associations in DB
    associations = db.exec(
        select(ArticleTag).where(ArticleTag.article_id == art_id)
    ).all()
    associated_tag_ids = {a.tag_id for a in associations}
    assert associated_tag_ids == {tag1.id, tag2.id}

    # 4. Verify detail endpoint returns the tags
    detail_res = client.get(f"{settings.API_V1_STR}/articles/slug/{slug}")
    assert detail_res.status_code == 200
    tag_names = [t["name"] for t in detail_res.json()["tags"]]
    assert tag1_name in tag_names
    assert tag2_name in tag_names


def test_update_article_replaces_and_removes_tags(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create 3 tags: A, B, C
    tag_a = Tag(name=f"TagA-{random_lower_string()}")
    tag_b = Tag(name=f"TagB-{random_lower_string()}")
    tag_c = Tag(name=f"TagC-{random_lower_string()}")
    db.add_all([tag_a, tag_b, tag_c])
    db.commit()
    db.refresh(tag_a)
    db.refresh(tag_b)
    db.refresh(tag_c)

    # 2. Create article with Tag A and Tag B
    slug = f"tag-replace-{random_lower_string()}"
    create_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Replace Tags Story",
            "slug": slug,
            "body": "Content",
            "status": "published",
            "tag_ids": [tag_a.id, tag_b.id],
        },
    )
    assert create_res.status_code == 200
    art_id = uuid.UUID(create_res.json()["id"])

    # 3. Update article to have Tag B and Tag C (removing Tag A)
    patch_res = client.patch(
        f"{settings.API_V1_STR}/articles/{art_id}",
        headers=superuser_token_headers,
        json={"tag_ids": [tag_b.id, tag_c.id]},
    )
    assert patch_res.status_code == 200

    # 4. Verify ArticleTag associations in DB
    db.expire_all()
    associations = db.exec(
        select(ArticleTag).where(ArticleTag.article_id == art_id)
    ).all()
    associated_tag_ids = {a.tag_id for a in associations}
    assert associated_tag_ids == {tag_b.id, tag_c.id}
    assert tag_a.id not in associated_tag_ids

    # 5. Verify detail endpoint reflects updated tags
    detail_res = client.get(f"{settings.API_V1_STR}/articles/{art_id}")
    assert detail_res.status_code == 200
    tag_names = {t["name"] for t in detail_res.json()["tags"]}
    assert tag_names == {tag_b.name, tag_c.name}


def test_update_article_with_empty_tags_removes_all_associations(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create tag
    tag = Tag(name=f"TagEmpty-{random_lower_string()}")
    db.add(tag)
    db.commit()
    db.refresh(tag)

    # 2. Create article with the tag
    create_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Clear Tags Story",
            "slug": f"clear-tags-{random_lower_string()}",
            "body": "Content",
            "status": "published",
            "tag_ids": [tag.id],
        },
    )
    assert create_res.status_code == 200
    art_id = uuid.UUID(create_res.json()["id"])

    # 3. Clear all tags by sending empty list
    patch_res = client.patch(
        f"{settings.API_V1_STR}/articles/{art_id}",
        headers=superuser_token_headers,
        json={"tag_ids": []},
    )
    assert patch_res.status_code == 200

    # 4. Verify zero associations in DB
    db.expire_all()
    associations = db.exec(
        select(ArticleTag).where(ArticleTag.article_id == art_id)
    ).all()
    assert len(associations) == 0

    # 5. Verify detail endpoint returns empty tags list
    detail_res = client.get(f"{settings.API_V1_STR}/articles/{art_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["tags"] == []


def test_create_article_with_invalid_tag_id_returns_400(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Invalid Tag Story",
            "slug": f"invalid-tag-{random_lower_string()}",
            "body": "Content",
            "status": "published",
            "tag_ids": [999999],
        },
    )
    assert r.status_code == 400
    assert "Tag with id 999999 does not exist" in r.json()["detail"]


def test_update_article_with_invalid_tag_id_returns_400(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    # 1. Create article
    create_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Update Invalid Tag Story",
            "slug": f"update-invalid-tag-{random_lower_string()}",
            "body": "Content",
            "status": "published",
        },
    )
    assert create_res.status_code == 200
    art_id = create_res.json()["id"]

    # 2. Try to update with non-existent tag
    patch_res = client.patch(
        f"{settings.API_V1_STR}/articles/{art_id}",
        headers=superuser_token_headers,
        json={"tag_ids": [888888]},
    )
    assert patch_res.status_code == 400
    assert "Tag with id 888888 does not exist" in patch_res.json()["detail"]


def test_article_rich_text_formatting_and_sanitization(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    rich_html_body = """
    <h2>Campus Breakthrough</h2>
    <p>This is a <strong>major</strong> editorial piece with <em>emphasis</em> and <u>underline</u>.</p>
    <blockquote><p>Student journalism matters more than ever.</p></blockquote>
    <ul>
        <li>First highlight</li>
        <li>Second highlight</li>
    </ul>
    <p>Read more at <a href="https://cdlb.edu.ph" target="_blank" rel="noopener noreferrer">official site</a>.</p>
    <img src="https://cdlb.edu.ph/images/campus.jpg" alt="Campus Quad" />
    <script>alert('malicious script')</script>
    <p onclick="stealCookies()">Clean paragraph</p>
    """

    create_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json={
            "headline": "Rich Text Story",
            "slug": f"rich-story-{random_lower_string()}",
            "body": rich_html_body,
            "status": "published",
        },
    )
    assert create_res.status_code == 200
    saved_article = create_res.json()
    saved_body = saved_article["body"]

    # Verify safe rich formatting is preserved
    assert "<h2>Campus Breakthrough</h2>" in saved_body
    assert "<strong>major</strong>" in saved_body
    assert "<em>emphasis</em>" in saved_body
    assert "<u>underline</u>" in saved_body
    assert "<blockquote><p>Student journalism matters more than ever.</p></blockquote>" in saved_body
    assert "<ul><li>First highlight</li><li>Second highlight</li></ul>" in saved_body or ("<li>First highlight</li>" in saved_body and "<li>Second highlight</li>" in saved_body)
    assert 'href="https://cdlb.edu.ph"' in saved_body
    assert 'src="https://cdlb.edu.ph/images/campus.jpg"' in saved_body
    assert 'alt="Campus Quad"' in saved_body

    # Verify unsafe script and event handlers were completely stripped
    assert "<script>" not in saved_body
    assert "alert('malicious script')" not in saved_body
    assert "onclick" not in saved_body
    assert "stealCookies" not in saved_body


def _create_published(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload = {
        "headline": "Campus Solar Caravan Hits the Road",
        "slug": f"search-solar-{random_lower_string()}",
        "excerpt": "Students showcased the solar caravan across Laguna.",
        "body": "<p>Students drove the campus solar caravan through neighboring towns this week.</p>",
        "status": "published",
    }
    payload.update(overrides)
    r = client.post(f"{settings.API_V1_STR}/articles/", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_public_search_matches_headline(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    created = _create_published(client, superuser_token_headers)
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "Caravan", "limit": 20},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert any(a["slug"] == created["slug"] for a in data["data"])


def test_public_search_matches_body(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    created = _create_published(client, superuser_token_headers)
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "neighboring", "limit": 20},
    )
    assert r.status_code == 200
    data = r.json()
    assert any(a["slug"] == created["slug"] for a in data["data"])


def test_public_search_multiword_query(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    _create_published(client, superuser_token_headers)
    # Multiple space-separated words should still return a relevant article.
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "solar caravan", "limit": 20},
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_public_search_irrelevant_query_returns_no_results(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    _create_published(client, superuser_token_headers)
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "zzzz-qwerty-unrelated-term-1234", "limit": 20},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["data"] == []


def test_public_search_excludes_unpublished_articles(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    _create_published(client, superuser_token_headers)
    # Draft article that should NOT appear in public search results.
    _create_published(
        client,
        superuser_token_headers,
        headline="Solar Caravan Draft That Must Stay Hidden",
        status="draft",
    )
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "Caravan", "limit": 50},
    )
    assert r.status_code == 200
    data = r.json()
    for a in data["data"]:
        assert a["status"] == "published"
    assert not any("Draft" in a["headline"] for a in data["data"])


def test_search_response_contract_preserved(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    _create_published(client, superuser_token_headers)
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        params={"search": "Caravan", "limit": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert {"data", "count"} <= set(body)
    assert isinstance(body["count"], int)
    assert isinstance(body["data"], list)


_VALID_COVER_IMAGE_URLS = [
    "/uploads/article/cover.png",
    "https://images.example.com/cover.png",
    "http://images.example.com/cover.png",
    "  https://images.example.com/cover.png  ",
]

_EXPECTED_COVER_IMAGE_URLS = [
    "/uploads/article/cover.png",
    "https://images.example.com/cover.png",
    "http://images.example.com/cover.png",
    "https://images.example.com/cover.png",
]

_INVALID_COVER_IMAGE_URLS = [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "blob:https://evil.com/abc",
    "//evil.com/cover.png",
    "evil.com/cover.png",
    "https://user:pass@evil.com/cover.png",
    "https://evil.com/\x00cover.png",
    "https://evil.com/\r\nInjected: 1",
]


def _create_article_with_cover(
    client: TestClient,
    headers: dict[str, str],
    cover_image_url: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "headline": "Cover Image Validation Test",
        "slug": f"cover-validation-{random_lower_string()}",
        "excerpt": "Testing cover image URL validation.",
        "body": "<p>Test body.</p>",
        "status": "published",
    }
    if cover_image_url is not None:
        payload["cover_image_url"] = cover_image_url
    r = client.post(f"{settings.API_V1_STR}/articles/", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return cast(dict[str, Any], r.json())


@pytest.mark.parametrize(("cover_image_url", "expected"), list(zip(_VALID_COVER_IMAGE_URLS, _EXPECTED_COVER_IMAGE_URLS, strict=True)))
def test_create_article_with_valid_cover_image_url(
    client: TestClient, superuser_token_headers: dict[str, str], cover_image_url: str, expected: str
) -> None:
    created = _create_article_with_cover(client, superuser_token_headers, cover_image_url)
    assert created["cover_image_url"] == expected


def test_create_article_without_cover_image_url(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    created = _create_article_with_cover(client, superuser_token_headers)
    assert created["cover_image_url"] is None


def test_create_article_with_blank_cover_image_url_set_to_none(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_article_with_cover(client, superuser_token_headers, "")
    assert created["cover_image_url"] is None


@pytest.mark.parametrize("cover_image_url", _INVALID_COVER_IMAGE_URLS)
def test_create_article_rejects_invalid_cover_image_url(
    client: TestClient, superuser_token_headers: dict[str, str], cover_image_url: str
) -> None:
    payload: dict[str, Any] = {
        "headline": "Cover Image Validation Test",
        "slug": f"cover-validation-{random_lower_string()}",
        "excerpt": "Testing cover image URL validation.",
        "body": "<p>Test body.</p>",
        "status": "published",
        "cover_image_url": cover_image_url,
    }
    r = client.post(f"{settings.API_V1_STR}/articles/", headers=superuser_token_headers, json=payload)
    assert r.status_code == 422


def test_update_article_with_valid_cover_image_url(client: TestClient, superuser_token_headers: dict[str, str]) -> None:
    created = _create_article_with_cover(client, superuser_token_headers, "/uploads/original.png")
    assert created["cover_image_url"] == "/uploads/original.png"
    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=superuser_token_headers,
        json={"cover_image_url": "https://new.example.com/cover.png"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cover_image_url"] == "https://new.example.com/cover.png"
    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=superuser_token_headers,
        json={"headline": "Updated headline only"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cover_image_url"] == "https://new.example.com/cover.png"


def test_update_article_with_blank_cover_image_url_clears_cover_image(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_article_with_cover(client, superuser_token_headers, "/uploads/original.png")
    assert created["cover_image_url"] == "/uploads/original.png"
    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=superuser_token_headers,
        json={"cover_image_url": ""},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cover_image_url"] is None


@pytest.mark.parametrize("cover_image_url", _INVALID_COVER_IMAGE_URLS)
def test_update_article_rejects_invalid_cover_image_url(
    client: TestClient, superuser_token_headers: dict[str, str], cover_image_url: str
) -> None:
    created = _create_article_with_cover(client, superuser_token_headers, "/uploads/original.png")
    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=superuser_token_headers,
        json={"cover_image_url": cover_image_url},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# D1 regression: unpublished-article visibility is author-only
# ---------------------------------------------------------------------------
#
# The codebase has no reviewer-assignment model, so the contract is:
#   published  -> anyone (anonymous included)
#   draft/pending/archived -> author only; everyone else gets 404
#
# These tests cover both the slug and ID read endpoints and the full role
# matrix: author, unrelated contributor, unrelated admin, unrelated
# super-admin, unrelated developer, and anonymous.


def _make_user_with_role(
    client: TestClient,
    db: Session,
    *,
    role: UserRole,
    is_superuser: bool = False,
    is_developer: bool = False,
) -> dict[str, str]:
    """Create a fresh user with the given role and return auth headers."""
    email = random_email()
    password = random_lower_string()
    from app import crud
    user_in = UserCreate(
        email=email,
        password=password,
        role=role,
        is_superuser=is_superuser,
        is_developer=is_developer,
    )
    crud.create_user(session=db, user_create=user_in)
    return authentication_token_from_email(
        client=client, email=email, db=db
    )


def _create_draft_article(
    client: TestClient,
    headers: dict[str, str],
    slug: str,
) -> dict[str, Any]:
    data = {
        "headline": f"Draft {slug}",
        "slug": slug,
        "body": "Draft body content",
        "status": "draft",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json=data,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _create_published_article(
    client: TestClient,
    headers: dict[str, str],
    slug: str,
) -> dict[str, Any]:
    data = {
        "headline": f"Published {slug}",
        "slug": slug,
        "body": "Published body content",
        "status": "published",
    }
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json=data,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_d1_author_can_retrieve_own_draft_by_slug(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    created = _create_draft_article(client, author_headers, "d1-author-slug")

    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=author_headers,
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_d1_author_can_retrieve_own_draft_by_id(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    created = _create_draft_article(client, author_headers, "d1-author-id")

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=author_headers,
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_d1_unrelated_contributor_cannot_retrieve_draft(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    other_headers = _make_user_with_role(client, db, role=UserRole.contributor)

    created = _create_draft_article(client, author_headers, "d1-unrelated-contrib")

    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=other_headers,
    )
    assert r.status_code == 404

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=other_headers,
    )
    assert r.status_code == 404


def test_d1_unrelated_admin_cannot_retrieve_draft(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    admin_headers = _make_user_with_role(client, db, role=UserRole.admin)

    created = _create_draft_article(client, author_headers, "d1-unrelated-admin")

    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=admin_headers,
    )
    assert r.status_code == 404

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=admin_headers,
    )
    assert r.status_code == 404


def test_d1_unrelated_super_admin_cannot_retrieve_draft(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)

    created = _create_draft_article(client, author_headers, "d1-unrelated-superadmin")

    # superuser_token_headers is settings.FIRST_SUPERUSER, an unrelated super admin
    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_d1_unrelated_developer_cannot_retrieve_draft(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    dev_headers = _make_user_with_role(
        client, db, role=UserRole.contributor, is_developer=True
    )

    created = _create_draft_article(client, author_headers, "d1-unrelated-dev")

    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=dev_headers,
    )
    assert r.status_code == 404

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=dev_headers,
    )
    assert r.status_code == 404


def test_d1_anonymous_cannot_retrieve_draft(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    created = _create_draft_article(client, author_headers, "d1-anon")

    r = client.get(f"{settings.API_V1_STR}/articles/slug/{created['slug']}")
    assert r.status_code == 404

    r = client.get(f"{settings.API_V1_STR}/articles/{created['id']}")
    assert r.status_code == 404


def test_d1_unauthorized_returns_404_not_403(
    client: TestClient, db: Session
) -> None:
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    other_headers = _make_user_with_role(client, db, role=UserRole.admin)

    created = _create_draft_article(client, author_headers, "d1-404-not-403")

    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=other_headers,
    )
    assert r.status_code == 404
    assert r.status_code != 403

    r = client.get(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=other_headers,
    )
    assert r.status_code == 404
    assert r.status_code != 403


def test_d1_published_articles_remain_publicly_accessible(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    other_headers = _make_user_with_role(client, db, role=UserRole.admin)

    # Contributors cannot create published articles (route coerces to pending),
    # so use the superuser fixture to produce a real published article.
    created = _create_published_article(
        client, superuser_token_headers, "d1-published-still-public"
    )

    # anonymous
    r = client.get(f"{settings.API_V1_STR}/articles/slug/{created['slug']}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == created["id"]

    r = client.get(f"{settings.API_V1_STR}/articles/{created['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == created["id"]

    # unrelated admin
    r = client.get(
        f"{settings.API_V1_STR}/articles/slug/{created['slug']}",
        headers=other_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == created["id"]


def test_d5_contributor_patch_publish_coerces_and_keeps_date_published_null(
    client: TestClient, db: Session
) -> None:
    """Contributor PATCH with status=published must be coerced to pending
    AND must NOT set date_published. Invariant: date_published IS NOT NULL
    implies status == published.
    """
    author_headers = _make_user_with_role(client, db, role=UserRole.contributor)
    created = _create_draft_article(client, author_headers, "d5-contributor-coerce")

    assert created["date_published"] is None
    assert created["status"] == "draft"

    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=author_headers,
        json={"status": "published"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending", (
        "Contributor must have status coerced from 'published' to 'pending'"
    )
    assert body["date_published"] is None, (
        "Contributor PATCH must NOT set date_published when status is coerced"
    )

    db.expire_all()
    persisted = db.exec(
        select(Article).where(Article.id == uuid.UUID(created["id"]))
    ).one()
    assert persisted.status.value == "pending"
    assert persisted.date_published is None, (
        "Persisted row must have date_published=NULL after coerced PATCH"
    )


def test_d5_admin_patch_publish_sets_date_published(
    client: TestClient, db: Session
) -> None:
    """Admin PATCH with status=published must succeed and set date_published.
    Invariant: date_published IS NOT NULL implies status == published.
    """
    admin_headers = _make_user_with_role(
        client, db, role=UserRole.admin, is_superuser=False
    )
    created = _create_draft_article(client, admin_headers, "d5-admin-publish")

    assert created["date_published"] is None
    assert created["status"] == "draft"

    r = client.patch(
        f"{settings.API_V1_STR}/articles/{created['id']}",
        headers=admin_headers,
        json={"status": "published"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "published"
    assert body["date_published"] is not None, (
        "Admin PATCH status=published must set date_published"
    )

    db.expire_all()
    persisted = db.exec(
        select(Article).where(Article.id == uuid.UUID(created["id"]))
    ).one()
    assert persisted.status.value == "published"
    assert persisted.date_published is not None
