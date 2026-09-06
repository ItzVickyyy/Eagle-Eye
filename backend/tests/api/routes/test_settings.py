import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import SiteSetting, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_get_site_settings_public(client: TestClient, db: Session) -> None:
    key = f"test_public_{uuid.uuid4().hex[:8]}"
    db.add(SiteSetting(key=key, value="val"))
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/settings/")
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "count" in data
    keys = [s["key"] for s in data["data"]]
    assert key in keys


def test_get_site_setting_by_key(client: TestClient, db: Session) -> None:
    key = f"test_by_key_{uuid.uuid4().hex[:8]}"
    db.add(SiteSetting(key=key, value="hello"))
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/settings/{key}")
    assert r.status_code == 200
    assert r.json()["key"] == key
    assert r.json()["value"] == "hello"


def test_get_site_setting_by_key_not_found(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/settings/nonexistent_key_xyz")
    assert r.status_code == 404


def test_set_site_setting_creates_new(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    key = f"new_setting_{uuid.uuid4().hex[:8]}"
    r = client.post(
        f"{settings.API_V1_STR}/settings/",
        headers=superuser_token_headers,
        json={"key": key, "value": "created"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == key
    assert body["value"] == "created"

    row = db.get(SiteSetting, key)
    assert row is not None
    assert row.value == "created"


def test_set_site_setting_updates_existing(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    key = f"update_setting_{uuid.uuid4().hex[:8]}"
    db.add(SiteSetting(key=key, value="old"))
    db.commit()

    r = client.post(
        f"{settings.API_V1_STR}/settings/",
        headers=superuser_token_headers,
        json={"key": key, "value": "new"},
    )
    assert r.status_code == 200
    assert r.json()["value"] == "new"


def test_set_site_setting_forbidden_for_admin(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.admin
        ),
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)
    r = client.post(
        f"{settings.API_V1_STR}/settings/",
        headers=headers,
        json={"key": "k", "value": "v"},
    )
    assert r.status_code == 403


def test_set_site_setting_requires_auth(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/settings/",
        json={"key": "k", "value": "v"},
    )
    assert r.status_code == 401


def test_delete_site_setting(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    key = f"del_setting_{uuid.uuid4().hex[:8]}"
    db.add(SiteSetting(key=key, value="to_delete"))
    db.commit()

    r = client.delete(
        f"{settings.API_V1_STR}/settings/{key}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Setting deleted successfully"
    assert db.get(SiteSetting, key) is None


def test_delete_site_setting_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/settings/nonexistent_del",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404
