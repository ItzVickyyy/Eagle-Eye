from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    ContactMessage,
    ContactMessageStatus,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_public_submit_contact_form(client: TestClient, db: Session) -> None:
    data = {
        "name": "Maria Santos",
        "email": "maria@cdlb.edu.ph",
        "subject": "Story Tip: Sports Festival",
        "message": "The annual sports fest starts next week at the gym.",
    }
    r = client.post(
        f"{settings.API_V1_STR}/contact/",
        json=data,
    )
    assert r.status_code == 200
    assert "Your message has been sent successfully" in r.json()["message"]

    # Verify persisted with status new
    msg = db.exec(
        select(ContactMessage).where(ContactMessage.email == "maria@cdlb.edu.ph")
    ).first()
    assert msg is not None
    assert msg.name == "Maria Santos"
    assert msg.subject == "Story Tip: Sports Festival"
    assert msg.status == ContactMessageStatus.new


def test_admin_read_and_filter_contact_messages(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    # 1. Create a new message and a read message
    msg1 = ContactMessage(
        name="Student One",
        email=random_email(),
        subject="Query 1",
        message="Message content 1",
        status=ContactMessageStatus.new,
    )
    msg2 = ContactMessage(
        name="Student Two",
        email=random_email(),
        subject="Query 2",
        message="Message content 2",
        status=ContactMessageStatus.read,
    )
    db.add(msg1)
    db.add(msg2)
    db.commit()
    db.refresh(msg1)
    db.refresh(msg2)

    # 2. List all messages
    r = client.get(
        f"{settings.API_V1_STR}/contact/",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 2
    assert any(m["id"] == msg1.id for m in data["data"])

    # 3. Filter by status=new
    r_new = client.get(
        f"{settings.API_V1_STR}/contact/?status=new",
        headers=superuser_token_headers,
    )
    assert r_new.status_code == 200
    new_data = r_new.json()["data"]
    assert any(m["id"] == msg1.id for m in new_data)
    assert not any(m["id"] == msg2.id for m in new_data)


def test_admin_get_message_detail_and_toggle_read_unread(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    msg = ContactMessage(
        name="Inquirer",
        email=random_email(),
        subject="Important Inquiry",
        message="Full detailed question here.",
        status=ContactMessageStatus.new,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # 1. Get message by ID
    r_detail = client.get(
        f"{settings.API_V1_STR}/contact/{msg.id}",
        headers=superuser_token_headers,
    )
    assert r_detail.status_code == 200
    assert r_detail.json()["message"] == "Full detailed question here."

    # 2. Mark as read
    r_read = client.patch(
        f"{settings.API_V1_STR}/contact/{msg.id}/mark-read",
        headers=superuser_token_headers,
    )
    assert r_read.status_code == 200
    assert r_read.json()["status"] == "read"

    # 3. Mark as unread
    r_unread = client.patch(
        f"{settings.API_V1_STR}/contact/{msg.id}/mark-unread",
        headers=superuser_token_headers,
    )
    assert r_unread.status_code == 200
    assert r_unread.json()["status"] == "new"


def test_admin_delete_contact_message(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    msg = ContactMessage(
        name="Delete Me",
        email=random_email(),
        subject="To Be Deleted",
        message="Delete this message.",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    msg_id = msg.id
    assert msg_id is not None

    # Delete message
    del_r = client.delete(
        f"{settings.API_V1_STR}/contact/{msg_id}",
        headers=superuser_token_headers,
    )
    assert del_r.status_code == 200
    assert del_r.json()["message"] == "Message deleted successfully"

    # Verify deleted from DB
    db.expire_all()
    assert db.get(ContactMessage, msg_id) is None


def test_unauthorized_users_cannot_access_contact_inbox(
    client: TestClient, db: Session
) -> None:
    # 1. Unauthenticated request
    assert client.get(f"{settings.API_V1_STR}/contact/").status_code == 401
    assert client.get(f"{settings.API_V1_STR}/contact/1").status_code == 401
    assert client.patch(f"{settings.API_V1_STR}/contact/1/mark-read").status_code == 401
    assert client.delete(f"{settings.API_V1_STR}/contact/1").status_code == 401

    # 2. Contributor user request
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, role=UserRole.contributor)
    from app import crud
    crud.create_user(session=db, user_create=user_in)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    assert client.get(f"{settings.API_V1_STR}/contact/", headers=headers).status_code == 403
    assert client.get(f"{settings.API_V1_STR}/contact/1", headers=headers).status_code == 403
    assert client.patch(f"{settings.API_V1_STR}/contact/1/mark-read", headers=headers).status_code == 403
    assert client.patch(f"{settings.API_V1_STR}/contact/1/mark-unread", headers=headers).status_code == 403
    assert client.delete(f"{settings.API_V1_STR}/contact/1", headers=headers).status_code == 403
