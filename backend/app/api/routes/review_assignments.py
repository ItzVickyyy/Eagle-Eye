import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_admin,
)
from app.core.audit import write_audit_log
from app.models import (
    Article,
    ArticleStatus,
    Message,
    ReviewAssignment,
    ReviewAssignmentCreate,
    ReviewAssignmentDetailPublic,
    ReviewAssignmentStatus,
    ReviewAssignmentsPublic,
    User,
    UserRole,
)

router = APIRouter(prefix="/review-assignments", tags=["review-assignments"])


def _get_active_assignment_for_article(
    session: Any,
    article_id: uuid.UUID,
) -> ReviewAssignment | None:
    """Return the active assignment for an article, if one exists."""
    return session.exec(
        select(ReviewAssignment).where(
            ReviewAssignment.article_id == article_id,
            ReviewAssignment.status == ReviewAssignmentStatus.active,
        )
    ).first()


@router.get(
    "/article/{article_id}",
    response_model=ReviewAssignmentsPublic,
    dependencies=[Depends(get_current_admin)],
)
def list_assignments_for_article(
    *,
    session: SessionDep,
    article_id: uuid.UUID,
) -> Any:
    """
    List review assignments for a specific article.
    Requires admin privileges.
    """
    article = session.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    statement = (
        select(ReviewAssignment)
        .where(ReviewAssignment.article_id == article_id)
        .order_by(col(ReviewAssignment.created_at).desc())
    )
    assignments = session.exec(statement).all()

    result: list[ReviewAssignmentDetailPublic] = []
    for a in assignments:
        detail = ReviewAssignmentDetailPublic.model_validate(a)
        if a.reviewer:
            from app.models import UserPublic

            detail.reviewer = UserPublic.model_validate(a.reviewer)
        if a.assigned_by_user:
            from app.models import UserPublic

            detail.assigned_by_user = UserPublic.model_validate(a.assigned_by_user)
        result.append(detail)

    return ReviewAssignmentsPublic(data=result, count=len(result))


@router.post(
    "/",
    response_model=ReviewAssignmentDetailPublic,
    dependencies=[Depends(get_current_admin)],
)
def create_assignment(
    *,
    session: SessionDep,
    assignment_in: ReviewAssignmentCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Assign a reviewer to an article.
    - Only admins can create assignments.
    - Article must be in pending status.
    - Only one active assignment per article.
    - Reviewer must be an admin or contributor.
    - Cannot assign the article's own author as reviewer.
    """
    article = session.get(Article, assignment_in.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.status != ArticleStatus.pending:
        raise HTTPException(
            status_code=400,
            detail="Can only assign reviewers to articles in pending status",
        )

    reviewer = session.get(User, assignment_in.reviewer_id)
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    if not reviewer.is_active:
        raise HTTPException(
            status_code=400, detail="Reviewer must be an active user"
        )

    if reviewer.id == article.author_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign the article's author as their own reviewer",
        )

    if reviewer.role not in (UserRole.admin, UserRole.super_admin, UserRole.contributor):
        raise HTTPException(
            status_code=400, detail="Reviewer must have an admin or contributor role"
        )

    existing = _get_active_assignment_for_article(session, assignment_in.article_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active assignment already exists for this article. Remove it first.",
        )

    assignment = ReviewAssignment(
        article_id=assignment_in.article_id,
        reviewer_id=assignment_in.reviewer_id,
        assigned_by=current_user.id,
        status=ReviewAssignmentStatus.active,
        notes=assignment_in.notes,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    write_audit_log(
        session=session,
        event="review_assignment.created",
        component="article",
        actor=current_user,
        target_type="review_assignment",
        target_id=str(assignment.id),
        success=True,
        message=f"Assigned reviewer {reviewer.email} to article {article.headline}",
    )
    session.commit()

    detail = ReviewAssignmentDetailPublic.model_validate(assignment)
    if reviewer:
        from app.models import UserPublic

        detail.reviewer = UserPublic.model_validate(reviewer)
    if assignment.assigned_by_user:
        from app.models import UserPublic

        detail.assigned_by_user = UserPublic.model_validate(
            assignment.assigned_by_user
        )
    return detail


@router.delete(
    "/{assignment_id}",
    response_model=Message,
    dependencies=[Depends(get_current_admin)],
)
def remove_assignment(
    *,
    session: SessionDep,
    assignment_id: uuid.UUID,
    current_user: CurrentUser,
) -> Message:
    """
    Remove (cancel) a review assignment.
    Only admins can remove assignments.
    """
    assignment = session.get(ReviewAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    article = session.get(Article, assignment.article_id)
    reviewer = session.get(User, assignment.reviewer_id)

    write_audit_log(
        session=session,
        event="review_assignment.removed",
        component="article",
        actor=current_user,
        target_type="review_assignment",
        target_id=str(assignment.id),
        success=True,
        message=f"Removed reviewer {reviewer.email if reviewer else 'unknown'} from article {article.headline if article else 'unknown'}",
    )
    session.delete(assignment)
    session.commit()
    return Message(message="Assignment removed successfully")


@router.get(
    "/my-assignments",
    response_model=ReviewAssignmentsPublic,
)
def list_my_assignments(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    List review assignments for the current user (as reviewer).
    """
    statement = (
        select(ReviewAssignment)
        .where(
            ReviewAssignment.reviewer_id == current_user.id,
            ReviewAssignment.status == ReviewAssignmentStatus.active,
        )
        .order_by(col(ReviewAssignment.created_at).desc())
    )
    assignments = session.exec(statement).all()

    result: list[ReviewAssignmentDetailPublic] = []
    for a in assignments:
        detail = ReviewAssignmentDetailPublic.model_validate(a)
        if a.article:
            from app.models import ArticlePublic

            # Attach minimal article info
            pass
        if a.reviewer:
            from app.models import UserPublic

            detail.reviewer = UserPublic.model_validate(a.reviewer)
        if a.assigned_by_user:
            from app.models import UserPublic

            detail.assigned_by_user = UserPublic.model_validate(
                a.assigned_by_user
            )
        result.append(detail)

    return ReviewAssignmentsPublic(data=result, count=len(result))
