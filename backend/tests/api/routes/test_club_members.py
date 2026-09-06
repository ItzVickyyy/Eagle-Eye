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
