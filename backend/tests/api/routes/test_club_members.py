from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import ClubMember, UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def _seed_member(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    is_active: bool = True,
    is_officer: bool = False,
    sort_order: int = 0,
) -> ClubMember:
    member = ClubMember(
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
        is_officer=is_officer,
        sort_order=sort_order,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def test_read_active_members_public(client: TestClient, db: Session) -> None:
    _seed_member(db, first_name="Act", last_name="Ive", is_active=True)
    _seed_member(db, first_name="In", last_name="Act", is_active=False)

    r = client.get(f"{settings.API_V1_STR}/club-members/")
    assert r.status_code == 200
    data = r.json()
    names = [m["first_name"] for m in data["data"]]
    assert "Act" in names
    assert "In" not in names
    assert data["count"] == len(data["data"])


def test_active_members_order_officer_before_non_officer(
    client: TestClient, db: Session
) -> None:
    _seed_member(db, first_name="Non", last_name="Officer", is_officer=False, sort_order=0)
    _seed_member(db, first_name="Yes", last_name="Officer", is_officer=True, sort_order=0)

    r = client.get(f"{settings.API_V1_STR}/club-members/")
    data = r.json()
    first_names = [m["first_name"] for m in data["data"]]
    assert first_names.index("Yes") < first_names.index("Non")


def test_read_all_members_admin(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    _seed_member(db, first_name="AllA", last_name="Active", is_active=True)
    _seed_member(db, first_name="AllI", last_name="Inactive", is_active=False)

    r = client.get(
        f"{settings.API_V1_STR}/club-members/all",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    names = [m["first_name"] for m in data["data"]]
    assert "AllI" in names
    assert data["count"] > 0


def test_read_all_members_forbidden_for_contributor(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.contributor
        ),
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)
    r = client.get(f"{settings.API_V1_STR}/club-members/all", headers=headers)
    assert r.status_code == 403


def test_create_club_member(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/club-members/",
        headers=superuser_token_headers,
        json={
            "first_name": "New",
            "last_name": "Member",
            "position": "Treasurer",
            "is_officer": True,
            "sort_order": 5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "New"
    assert body["last_name"] == "Member"
    assert body["is_officer"] is True
    assert body["sort_order"] == 5


def test_create_club_member_forbidden_for_admin(client: TestClient, db: Session) -> None:
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
        f"{settings.API_V1_STR}/club-members/",
        headers=headers,
        json={"first_name": "X", "last_name": "Y"},
    )
    assert r.status_code == 403


def test_update_club_member(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    member = _seed_member(db, first_name="Up", last_name="Date")
    assert member.id is not None

    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{member.id}",
        headers=superuser_token_headers,
        json={"first_name": "Updated", "position_title": "President"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Updated"
    assert body["position_title"] == "President"
    assert body["last_name"] == "Date"


def test_update_club_member_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/999999",
        headers=superuser_token_headers,
        json={"first_name": "No"},
    )
    assert r.status_code == 404


def test_delete_club_member(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    member = _seed_member(db, first_name="Del", last_name="Me")
    assert member.id is not None

    member_id = member.id
    r = client.delete(
        f"{settings.API_V1_STR}/club-members/{member_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    assert r.json()["message"] == "Club member deleted successfully"
    db.rollback()
    assert db.get(ClubMember, member_id) is None


def test_delete_club_member_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/club-members/999999",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404


def test_read_active_members_order_by_last_name(
    client: TestClient, db: Session
) -> None:
    _seed_member(db, first_name="Zeta", last_name="Zebra", is_active=True, sort_order=0)
    _seed_member(db, first_name="Alpha", last_name="Apple", is_active=True, sort_order=0)

    r = client.get(f"{settings.API_V1_STR}/club-members/")
    data = r.json()
    active = [m for m in data["data"] if m["first_name"] in ("Zeta", "Alpha")]
    last_names = [m["last_name"] for m in active]
    assert last_names == sorted(last_names)


_VALID_PHOTO_URLS = [
    "/uploads/foo.jpg",
    "/assets/foo.png",
    " /assets/leading-trailing.png ",
    "https://images.example.com/photo.png",
    "http://images.example.com/photo.png",
]
_EXPECTED_PHOTO_URLS = [
    "/uploads/foo.jpg",
    "/assets/foo.png",
    "/assets/leading-trailing.png",
    "https://images.example.com/photo.png",
    "http://images.example.com/photo.png",
]

_INVALID_PHOTO_URLS = [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    "blob:https://evil.com/abc",
    "//evil.com/photo.png",
    "evil.com/photo.png",
    "https://user:pass@evil.com/photo.png",
    "https://evil.com/\x00photo.png",
    "https://evil.com/\r\nInjected: 1",
]

_BLANK_PHOTO_URLS = ["", "   ", "\t", "\n"]


def _create_member_with_photo(
    client: TestClient,
    headers: dict[str, str],
    photo_url: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "first_name": "Photo",
        "last_name": "Member",
        "position": "Treasurer",
    }
    if photo_url is not None:
        payload["photo_url"] = photo_url
    r = client.post(
        f"{settings.API_V1_STR}/club-members/", headers=headers, json=payload
    )
    assert r.status_code == 200, r.text
    return cast(dict[str, Any], r.json())


@pytest.mark.parametrize(
    ("photo_url", "expected"),
    list(zip(_VALID_PHOTO_URLS, _EXPECTED_PHOTO_URLS, strict=True)),
)
def test_create_member_with_valid_photo_url(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    photo_url: str,
    expected: str,
) -> None:
    created = _create_member_with_photo(client, superuser_token_headers, photo_url)
    assert created["photo_url"] == expected


def test_create_member_without_photo_url(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_member_with_photo(client, superuser_token_headers)
    assert created["photo_url"] is None


@pytest.mark.parametrize("photo_url", _BLANK_PHOTO_URLS)
def test_create_member_with_blank_photo_url_set_to_none(
    client: TestClient, superuser_token_headers: dict[str, str], photo_url: str
) -> None:
    created = _create_member_with_photo(client, superuser_token_headers, photo_url)
    assert created["photo_url"] is None


@pytest.mark.parametrize("photo_url", _INVALID_PHOTO_URLS)
def test_create_member_rejects_invalid_photo_url(
    client: TestClient, superuser_token_headers: dict[str, str], photo_url: str
) -> None:
    payload: dict[str, Any] = {
        "first_name": "Photo",
        "last_name": "Member",
        "position": "Treasurer",
        "photo_url": photo_url,
    }
    r = client.post(
        f"{settings.API_V1_STR}/club-members/",
        headers=superuser_token_headers,
        json=payload,
    )
    assert r.status_code == 422


def test_update_member_with_valid_photo_url(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_member_with_photo(
        client, superuser_token_headers, "/uploads/original.png"
    )
    assert created["photo_url"] == "/uploads/original.png"
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{created['id']}",
        headers=superuser_token_headers,
        json={"photo_url": "https://new.example.com/photo.png"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "https://new.example.com/photo.png"
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{created['id']}",
        headers=superuser_token_headers,
        json={"first_name": "Updated"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "https://new.example.com/photo.png"


def test_update_member_without_photo_url_preserves_existing(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_member_with_photo(
        client, superuser_token_headers, "/uploads/original.png"
    )
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{created['id']}",
        headers=superuser_token_headers,
        json={"first_name": "Renamed"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] == "/uploads/original.png"


def test_update_member_with_blank_photo_url_clears_photo(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    created = _create_member_with_photo(
        client, superuser_token_headers, "/uploads/original.png"
    )
    assert created["photo_url"] == "/uploads/original.png"
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{created['id']}",
        headers=superuser_token_headers,
        json={"photo_url": ""},
    )
    assert r.status_code == 200, r.text
    assert r.json()["photo_url"] is None


@pytest.mark.parametrize("photo_url", _INVALID_PHOTO_URLS)
def test_update_member_rejects_invalid_photo_url(
    client: TestClient, superuser_token_headers: dict[str, str], photo_url: str
) -> None:
    created = _create_member_with_photo(
        client, superuser_token_headers, "/uploads/original.png"
    )
    r = client.patch(
        f"{settings.API_V1_STR}/club-members/{created['id']}",
        headers=superuser_token_headers,
        json={"photo_url": photo_url},
    )
    assert r.status_code == 422
