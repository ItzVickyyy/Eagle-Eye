from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.models import Message, Tag, TagCreate, TagPublic, TagUpdate, TagsPublic

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=TagsPublic)
def read_tags(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    List tags (public).
    """
    statement = select(Tag).order_by(col(Tag.name).asc())
    count = session.exec(select(func.count()).select_from(Tag)).one()
    tags = session.exec(statement.offset(skip).limit(limit)).all()
    tags_public = [TagPublic.model_validate(t) for t in tags]
    return TagsPublic(data=tags_public, count=count)


@router.post("/", response_model=TagPublic)
def create_tag(
    *,
    session: SessionDep,
    tag_in: TagCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Create a tag.
    """
    cleaned_name = tag_in.name.strip().lower()
    existing = session.exec(select(Tag).where(func.lower(Tag.name) == cleaned_name)).first()
    if existing:
        return existing

    tag = Tag(name=tag_in.name.strip())
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.delete("/{id}", response_model=Message)
def delete_tag(
    *,
    session: SessionDep,
    id: int,
    current_user: AdminUser,
) -> Message:
    """
    Delete tag (Admin / Super Admin).
    """
    tag = session.get(Tag, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    session.delete(tag)
    session.commit()
    return Message(message="Tag deleted successfully")
