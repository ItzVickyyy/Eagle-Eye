import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep
from app.core.rate_limit import comment_rate_limiter
from app.models import (
    Article,
    Comment,
    CommentCreate,
    CommentPublic,
    CommentsPublic,
    CommentStatus,
    CommentUpdate,
    Message,
)

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/article/{article_id}", response_model=CommentsPublic)
def get_article_comments(
    article_id: uuid.UUID,
    session: SessionDep,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Get approved comments for an article (public).
    """
    statement = (
        select(Comment)
        .where(
            Comment.article_id == article_id,
            Comment.status == CommentStatus.approved,
        )
        .order_by(col(Comment.created_at).desc())
    )
    count = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    comments = session.exec(statement.offset(skip).limit(limit)).all()
    comments_public = [CommentPublic.model_validate(c) for c in comments]
    return CommentsPublic(data=comments_public, count=count)


@router.get("/", response_model=CommentsPublic)
def get_all_comments(
    session: SessionDep,
    _current_user: AdminUser,
    status: CommentStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    List all comments for moderation (Admin / Super Admin).
    """
    statement = select(Comment).order_by(col(Comment.created_at).desc())
    if status:
        statement = statement.where(Comment.status == status)

    count = session.exec(
        select(func.count()).select_from(statement.subquery())
    ).one()
    comments = session.exec(statement.offset(skip).limit(limit)).all()
    comments_public = []
    for c in comments:
        cp = CommentPublic.model_validate(c)
        if c.article:
            cp.article_headline = c.article.headline
            cp.article_slug = c.article.slug
        comments_public.append(cp)
    return CommentsPublic(data=comments_public, count=count)


@router.post(
    "/",
    response_model=CommentPublic,
    dependencies=[Depends(comment_rate_limiter)],
)
def create_comment(
    *,
    session: SessionDep,
    comment_in: CommentCreate,
) -> Any:
    """
    Submit comment on an article (public reader).
    Default is approved or pending depending on policy.
    """
    article = session.get(Article, comment_in.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comment = Comment(
        article_id=comment_in.article_id,
        guest_name=comment_in.guest_name,
        guest_email=comment_in.guest_email,
        body=comment_in.body,
        status=CommentStatus.approved,  # Auto-approved with moderation deletion capability
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.patch("/{id}", response_model=CommentPublic)
def update_comment_status(
    *,
    session: SessionDep,
    id: int,
    comment_in: CommentUpdate,
    _current_user: AdminUser,
) -> Any:
    """
    Moderate comment status (Admin / Super Admin).
    """
    comment = session.get(Comment, id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.status = comment_in.status
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.delete("/{id}", response_model=Message)
def delete_comment(
    *,
    session: SessionDep,
    id: int,
    _current_user: AdminUser,
) -> Message:
    """
    Delete comment (Admin / Super Admin).
    """
    comment = session.get(Comment, id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    session.delete(comment)
    session.commit()
    return Message(message="Comment deleted successfully")
