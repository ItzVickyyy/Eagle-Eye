import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Tag, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_read_tags_public(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/tags/")
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data


def test_create_tag(client: TestClient, normal_user_token_headers: dict[str, str]) -> None:
    name = f"tag-{uuid.uuid4().hex[:8]}"
    r = client.post(
        f"{settings.API_V1_STR}/tags/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == name
    assert "id" in body


def test_create_tag_deduplicates_case_insensitive(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    name = f"Dedup-{uuid.uuid4().hex[:8]}"
    r1 = client.post(
        f"{settings.API_V1_STR}/tags/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert r1.status_code == 200
    first_id = r1.json()["id"]

    r2 = client.post(
        f"{settings.API_V1_STR}/tags/",
        headers=normal_user_token_headers,
        json={"name": name.upper()},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == first_id


def test_create_tag_strips_whitespace(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    raw_name = f"  strip-{uuid.uuid4().hex[:8]}  "
    r = client.post(
        f"{settings.API_V1_STR}/tags/",
        headers=normal_user_token_headers,
        json={"name": raw_name},
    )
    assert r.status_code == 200
    assert r.json()["name"] == raw_name.strip()


def test_delete_tag(client: TestClient, superuser_token_headers: dict[str, str], db: Session) -> None:
    tag = Tag(name=f"del-tag-{uuid.uuid4().hex[:8]}")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    assert tag.id is not None

    tag_id = tag.id
    r = client.delete(
        f"{settings.API_V1_STR}/tags/{tag_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Tag deleted successfully"
    db.rollback()
    assert db.get(Tag, tag_id) is None


def test_delete_tag_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/tags/999999",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_delete_tag_forbidden_for_contributor(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.contributor
        ),
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)
    r = client.delete(f"{settings.API_V1_STR}/tags/1", headers=headers)
    assert r.status_code == 403
