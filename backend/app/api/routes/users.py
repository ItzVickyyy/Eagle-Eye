import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, func, select

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    is_super_admin,
)
from app.core.audit import write_audit_log
from app.core.captcha import verify_captcha
from app.core.config import settings
from app.core.flags import enforce_public_signup_enabled
from app.core.rate_limit import password_change_rate_limiter, signup_rate_limiter
from app.core.security import get_password_hash, verify_password
from app.core.token_store import bump_token_version
from app.models import (
    Message,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """

    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(
    *, session: SessionDep, user_in: UserCreate, current_user: CurrentUser
) -> Any:
    """
    Create new user.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = crud.create_user(session=session, user_create=user_in)
    write_audit_log(
        session=session,
        event="user.created",
        component="user",
        actor=current_user,
        target_type="user",
        target_id=str(user.id),
        success=True,
        message=f"Created user {user.email}",
    )
    session.commit()
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch(
    "/me/password",
    response_model=Message,
    dependencies=[Depends(password_change_rate_limiter)],
)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    bump_token_version(session=session, user=current_user)
    write_audit_log(
        session=session,
        event="auth.password_changed",
        component="auth",
        actor=current_user,
        success=True,
        message="Password updated; all other sessions invalidated",
    )
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if is_super_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


@router.post(
    "/signup",
    response_model=UserPublic,
    dependencies=[
        Depends(signup_rate_limiter),
        Depends(enforce_public_signup_enabled),
        Depends(verify_captcha),
    ],
)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    write_audit_log(
        session=session,
        event="user.created",
        component="user",
        target_type="user",
        target_id=str(user.id),
        success=True,
        message=f"New user registered {user.email}",
    )
    session.commit()
    return user


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not is_super_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    Update a user.
    """

    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    pending = user_in.model_dump(exclude_unset=True)
    event: str | None = None
    if "role" in pending and pending["role"] != db_user.role:
        event = "user.role_changed"
    elif "is_developer" in pending and pending["is_developer"] != db_user.is_developer:
        event = (
            "user.developer_access_granted"
            if pending["is_developer"]
            else "user.developer_access_revoked"
        )
    elif "is_active" in pending and pending["is_active"] != db_user.is_active:
        event = "user.activated" if pending["is_active"] else "user.deactivated"

    password_rotated = "password" in pending

    db_user = crud.update_user(session=session, db_user=db_user, user_in=user_in)

    if password_rotated:
        bump_token_version(session=session, user=db_user)
        write_audit_log(
            session=session,
            event="auth.password_changed_by_admin",
            component="auth",
            actor=current_user,
            target_type="user",
            target_id=str(db_user.id),
            success=True,
            message=(
                f"Admin {current_user.email} rotated password for "
                f"{db_user.email}; all of that user's sessions invalidated"
            ),
        )

    if event:
        write_audit_log(
            session=session,
            event=event,
            component="user",
            actor=current_user,
            target_type="user",
            target_id=str(db_user.id),
            success=True,
            message=f"Changed user {db_user.email} ({event})",
        )
    if event or password_rotated:
        session.commit()
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    write_audit_log(
        session=session,
        event="user.deleted",
        component="user",
        actor=current_user,
        target_type="user",
        target_id=str(user.id),
        success=True,
        message=f"Deleted user {user.email}",
    )
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
