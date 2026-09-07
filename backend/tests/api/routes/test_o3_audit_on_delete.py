"""Audit-log tests for destructive admin endpoints (O3 closure).

Verifies that the 6 admin-only hard-delete endpoints emit an audit event
through `app.core.audit.write_audit_log`:

- `club_members.py` DELETE  -> `club_member.deleted`
- `categories.py` DELETE    -> `category.deleted`
- `comments.py` DELETE      -> `comment.deleted`
- `tags.py` DELETE          -> `tag.deleted`
- `settings.py` DELETE      -> `site_setting.deleted`
- `contact.py` DELETE       -> `contact_message.deleted`
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Article,
    AuditLog,
    Category,
    ClubMember,
    Comment,
    CommentStatus,
    ContactMessage,
    SiteSetting,
    Tag,
)
from tests.utils.utils import random_email, random_lower_string


def _audit_events(db: Session, event: str) -> list[AuditLog]:
    return list(
        db.exec(
            select(AuditLog)
            .where(AuditLog.event == event)
            .order_by(AuditLog.id.desc())
        ).all()
    )


def _make_article(
    client: TestClient, headers: dict[str, str]
) -> Article:
    """Create a published article via the API (so author_id, slug, etc. are valid)."""
    suffix = random_lower_string()
    r = client.post(
        f"{settings.API_V1_STR}/articles/",
        headers=headers,
        json={
            "headline": f"audit-target-{suffix}",
            "slug": f"audit-target-{suffix}",
            "body": "<p>x</p>",
            "status": "published",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return Article.model_validate(data)


def test_club_member_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    member = ClubMember(
        first_name="Audit",
        last_name="Club",
        is_officer=False,
        is_active=True,
        sort_order=1,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    member_id = member.id

    r = client.delete(
        f"{settings.API_V1_STR}/club-members/{member_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "club_member.deleted")
    assert any(r.target_id == str(member_id) for r in rows)


def test_category_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    cat = Category(
        name=f"Audit Cat {random_lower_string()}",
        slug=f"audit-{random_lower_string()}",
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    cat_id = cat.id

    r = client.delete(
        f"{settings.API_V1_STR}/categories/{cat_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "category.deleted")
    assert any(r.target_id == str(cat_id) for r in rows)


def test_comment_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    art = _make_article(client, superuser_token_headers)
    c = Comment(
        article_id=art.id,
        guest_name="Guest",
        guest_email=random_email(),
        body="audit body",
        status=CommentStatus.pending,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    cid = c.id

    r = client.delete(
        f"{settings.API_V1_STR}/comments/{cid}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "comment.deleted")
    assert any(r.target_id == str(cid) for r in rows)


def test_tag_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    t = Tag(name=f"audittag-{random_lower_string()}")
    db.add(t)
    db.commit()
    db.refresh(t)
    tid = t.id

    r = client.delete(
        f"{settings.API_V1_STR}/tags/{tid}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "tag.deleted")
    assert any(r.target_id == str(tid) for r in rows)


def test_site_setting_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    key = f"audit_key_{random_lower_string()}"
    db.add(SiteSetting(key=key, value="v"))
    db.commit()

    r = client.delete(
        f"{settings.API_V1_STR}/settings/{key}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "site_setting.deleted")
    assert any(r.target_id == key for r in rows)


def test_contact_message_delete_emits_audit(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    msg = ContactMessage(
        name="Sender",
        email=random_email(),
        subject="audit subj",
        message="audit body",
        is_read=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    mid = msg.id

    r = client.delete(
        f"{settings.API_V1_STR}/contact/{mid}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    rows = _audit_events(db, "contact_message.deleted")
    assert any(r.target_id == str(mid) for r in rows)
