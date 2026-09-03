import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Article, ArticleStatus, Category, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_create_category_as_admin(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    slug = f"cat-{random_lower_string()}"
    data = {
        "name": "Campus Life",
        "slug": slug,
        "description": "Stories about student campus life",
    }
    r = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    created = r.json()
    assert created["name"] == data["name"]
    assert created["slug"] == slug
    assert "id" in created


def test_read_categories(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/categories/")
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
    assert isinstance(data["data"], list)


def test_read_category_by_id_and_slug(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    slug = f"read-{random_lower_string()}"
    data = {"name": "Read Test", "slug": slug}
    r = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    cat_id = r.json()["id"]

    # By ID
    r_id = client.get(f"{settings.API_V1_STR}/categories/{cat_id}")
    assert r_id.status_code == 200
    assert r_id.json()["slug"] == slug

    # By slug
    r_slug = client.get(f"{settings.API_V1_STR}/categories/{slug}")
    assert r_slug.status_code == 200
    assert r_slug.json()["id"] == cat_id


def test_delete_empty_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    slug = f"del-{random_lower_string()}"
    data = {"name": "Delete Me", "slug": slug}
    r = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    cat_id = r.json()["id"]

    # Delete
    del_r = client.delete(
        f"{settings.API_V1_STR}/categories/{cat_id}",
        headers=superuser_token_headers,
    )
    assert del_r.status_code == 200
    assert del_r.json()["message"] == "Category deleted successfully"

    # Verify deleted
    get_r = client.get(f"{settings.API_V1_STR}/categories/{cat_id}")
    assert get_r.status_code == 404


def test_delete_category_with_assigned_articles_sets_category_id_null(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """
    Regression test: When a category that contains articles is deleted by a Super Admin,
    the category is removed, but all assigned articles remain intact with category_id = NULL.
    """
    # 1. Create category
    cat_slug = f"assigned-cat-{random_lower_string()}"
    cat_data = {"name": "Category With Articles", "slug": cat_slug}
    cat_res = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
        json=cat_data,
    )
    assert cat_res.status_code == 200
    cat_id = cat_res.json()["id"]

    # 2. Create article assigned to this category
    article_headline = "Preserved Story Headline"
    article_slug = f"preserved-story-{random_lower_string()}"
    article_body = "<p>Valuable journalism content that must not be deleted.</p>"
    article_data = {
        "headline": article_headline,
        "slug": article_slug,
        "body": article_body,
        "category_id": cat_id,
        "status": "published",
    }
    art_res = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=superuser_token_headers,
        json=article_data,
    )
    assert art_res.status_code == 200
    art_id = art_res.json()["id"]
    assert art_res.json()["category_id"] == cat_id

    # 3. Delete the category
    del_res = client.delete(
        f"{settings.API_V1_STR}/categories/{cat_id}",
        headers=superuser_token_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Category deleted successfully"

    # 4. Verify category no longer exists
    assert client.get(f"{settings.API_V1_STR}/categories/{cat_id}").status_code == 404
    db.expire_all()
    assert db.exec(select(Category).where(Category.id == cat_id)).first() is None

    # 5. Verify article still exists in database and all metadata is preserved
    article_in_db = db.exec(
        select(Article).where(Article.id == uuid.UUID(art_id))
    ).first()
    assert article_in_db is not None
    assert article_in_db.headline == article_headline
    assert article_in_db.slug == article_slug
    assert article_in_db.body == article_body
    assert article_in_db.status == ArticleStatus.published
    assert article_in_db.category_id is None

    # 6. Verify article is still accessible via API and reports category_id as null
    get_art_res = client.get(f"{settings.API_V1_STR}/articles/slug/{article_slug}")
    assert get_art_res.status_code == 200
    detail = get_art_res.json()
    assert detail["id"] == str(art_id)
    assert detail["category_id"] is None
    assert detail["category"] is None
    assert detail["headline"] == article_headline


def test_delete_category_forbidden_for_contributor(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.contributor)
    from app import crud

    crud.create_user(session=db, user_create=user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    r = client.delete(f"{settings.API_V1_STR}/categories/1", headers=headers)
    assert r.status_code == 403
