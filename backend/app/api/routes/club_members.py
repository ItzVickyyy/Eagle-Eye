from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import AdminUser, SessionDep, SuperAdminUser
from app.models import (
    ClubMember,
    ClubMemberCreate,
    ClubMemberPublic,
    ClubMembersPublic,
    ClubMemberUpdate,
    Message,
)

router = APIRouter(prefix="/club-members", tags=["club-members"])


@router.get("/", response_model=ClubMembersPublic)
def read_active_members(session: SessionDep) -> Any:
    """
    List active club members for public About Us page.
    """
    statement = (
        select(ClubMember)
        .where(ClubMember.is_active == True)  # noqa: E712
        .order_by(
            col(ClubMember.is_officer).desc(),
            col(ClubMember.sort_order).asc(),
            col(ClubMember.last_name).asc(),
        )
    )
    members = session.exec(statement).all()
    members_public = [ClubMemberPublic.model_validate(m) for m in members]
    return ClubMembersPublic(data=members_public, count=len(members_public))


@router.get("/all", response_model=ClubMembersPublic)
def read_all_members(
    session: SessionDep,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    List all club members including inactive ones (Admin / Super Admin).
    """
    statement = select(ClubMember).order_by(
        col(ClubMember.sort_order).asc(),
        col(ClubMember.last_name).asc(),
    )
    count = session.exec(select(func.count()).select_from(ClubMember)).one()
    members = session.exec(statement.offset(skip).limit(limit)).all()
    members_public = [ClubMemberPublic.model_validate(m) for m in members]
    return ClubMembersPublic(data=members_public, count=count)


@router.post("/", response_model=ClubMemberPublic)
def create_club_member(
    *,
    session: SessionDep,
    member_in: ClubMemberCreate,
    current_user: SuperAdminUser,
) -> Any:
    """
    Create a new club member (Super Admin).
    """
    member = ClubMember.model_validate(member_in)
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


@router.patch("/{id}", response_model=ClubMemberPublic)
def update_club_member(
    *,
    session: SessionDep,
    id: int,
    member_in: ClubMemberUpdate,
    current_user: SuperAdminUser,
) -> Any:
    """
    Update club member info (Super Admin).
    """
    member = session.get(ClubMember, id)
    if not member:
        raise HTTPException(status_code=404, detail="Club member not found")

    update_dict = member_in.model_dump(exclude_unset=True)
    member.sqlmodel_update(update_dict)
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


@router.delete("/{id}", response_model=Message)
def delete_club_member(
    *,
    session: SessionDep,
    id: int,
    current_user: SuperAdminUser,
) -> Message:
    """
    Delete club member (Super Admin).
    """
    member = session.get(ClubMember, id)
    if not member:
        raise HTTPException(status_code=404, detail="Club member not found")
    session.delete(member)
    session.commit()
    return Message(message="Club member deleted successfully")
