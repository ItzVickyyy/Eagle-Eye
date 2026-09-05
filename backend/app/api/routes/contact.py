from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep
from app.core.captcha import verify_captcha
from app.core.config import settings
from app.core.flags import enforce_contact_form_enabled
from app.core.rate_limit import contact_rate_limiter
from app.models import (
    ContactMessage,
    ContactMessageCreate,
    ContactMessagePublic,
    ContactMessagesPublic,
    ContactMessageStatus,
    Message,
)
from app.utils import send_email

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "/",
    response_model=Message,
    dependencies=[
        Depends(contact_rate_limiter),
        Depends(enforce_contact_form_enabled),
        Depends(verify_captcha),
    ],
)
def submit_contact_form(
    *,
    session: SessionDep,
    msg_in: ContactMessageCreate,
) -> Message:
    """
    Public contact form submission. Saves message and optionally emails club.
    """
    msg = ContactMessage(
        name=msg_in.name,
        email=msg_in.email,
        subject=msg_in.subject,
        message=msg_in.message,
    )
    session.add(msg)
    session.commit()

    # If SMTP is configured, notify club email
    if settings.emails_enabled and settings.EMAILS_FROM_EMAIL:
        try:
            send_email(
                email_to=settings.EMAILS_FROM_EMAIL,
                subject=f"New Contact Form Submission: {msg_in.subject or 'General Inquiry'}",
                html_content=f"<p><strong>From:</strong> {msg_in.name} ({msg_in.email})</p><p><strong>Message:</strong><br>{msg_in.message}</p>",
            )
        except Exception:
            pass

    return Message(message="Your message has been sent successfully. Thank you!")


@router.get("/", response_model=ContactMessagesPublic)
def read_contact_messages(
    session: SessionDep,
    _current_user: AdminUser,
    status: ContactMessageStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    List contact messages (Admin / Super Admin).
    """
    statement = select(ContactMessage).order_by(col(ContactMessage.sent_at).desc())
    if status:
        statement = statement.where(ContactMessage.status == status)

    count = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    messages = session.exec(statement.offset(skip).limit(limit)).all()
    messages_public = [ContactMessagePublic.model_validate(m) for m in messages]
    return ContactMessagesPublic(data=messages_public, count=count)


@router.get("/{id}", response_model=ContactMessagePublic)
def get_contact_message(
    id: int,
    session: SessionDep,
    _current_user: AdminUser,
) -> Any:
    """
    Get contact message details (Admin / Super Admin).
    """
    msg = session.get(ContactMessage, id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


@router.patch("/{id}/mark-read", response_model=ContactMessagePublic)
def mark_message_read(
    *,
    session: SessionDep,
    id: int,
    _current_user: AdminUser,
) -> Any:
    """
    Mark contact message as read (Admin / Super Admin).
    """
    msg = session.get(ContactMessage, id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.status = ContactMessageStatus.read
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


@router.patch("/{id}/mark-unread", response_model=ContactMessagePublic)
def mark_message_unread(
    *,
    session: SessionDep,
    id: int,
    _current_user: AdminUser,
) -> Any:
    """
    Mark contact message as unread/new (Admin / Super Admin).
    """
    msg = session.get(ContactMessage, id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.status = ContactMessageStatus.new
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return msg


@router.delete("/{id}", response_model=Message)
def delete_contact_message(
    *,
    session: SessionDep,
    id: int,
    _current_user: AdminUser,
) -> Message:
    """
    Delete contact message (Admin / Super Admin).
    """
    msg = session.get(ContactMessage, id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    session.delete(msg)
    session.commit()
    return Message(message="Message deleted successfully")
