import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Article,
    ArticleStatus,
    ArticleTag,
    Category,
    Tag,
    User,
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
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
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
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
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


