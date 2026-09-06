import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.token_store import is_token_revoked
from app.models import TokenPayload, User, UserRole

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(reusable_oauth2)]


def _enforce_token_not_revoked(
    session: Session,
    token: str,  # noqa: ARG001 — kept for symmetry / future audit logging
    token_data: TokenPayload,
    user: User,
) -> None:
    """Reject tokens revoked by either layer (per-jti or per-user version).

    The two layers are:

    * ``User.token_version``: a single counter on the user. If the token's
      ``tv`` claim is missing or below the current value the token was
      issued before the user's last password change / reset and is invalid.
    * ``token_revocations``: explicit ``jti`` denylist. Used by
      ``POST /auth/logout``.

    Both checks use the same 401-with-``Could not validate credentials``
    error so the caller cannot tell them apart.
    """
    if token_data.tv is None or token_data.tv != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_data.jti and is_token_revoked(session, token_data.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    try:
        user_id = uuid.UUID(str(token_data.sub))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    _enforce_token_not_revoked(session, token, token_data, user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_current_user(session: SessionDep, token: TokenDep) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if not token_data.sub:
            return None
        user_id = uuid.UUID(str(token_data.sub))
        user = session.get(User, user_id)
        if not user or not user.is_active:
            return None
        _enforce_token_not_revoked(session, token, token_data, user)
        return user
    except Exception:
        return None
    return None


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


def is_super_admin(user: User) -> bool:
    return bool(user.is_superuser or user.role == UserRole.super_admin)


def is_admin_or_above(user: User) -> bool:
    return bool(
        user.is_superuser
        or user.role in (UserRole.super_admin, UserRole.admin)
    )


def is_developer(user: User) -> bool:
    return bool(user.is_developer)


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not (current_user.is_superuser or current_user.role == UserRole.super_admin):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user


def get_current_admin(current_user: CurrentUser) -> User:
    if not is_admin_or_above(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges (Admin required)"
        )
    return current_user


def get_current_developer(current_user: CurrentUser) -> User:
    if not is_developer(current_user):
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges (Developer access required)",
        )
    return current_user


AdminUser = Annotated[User, Depends(get_current_admin)]
SuperAdminUser = Annotated[User, Depends(get_current_active_superuser)]
DeveloperUser = Annotated[User, Depends(get_current_developer)]
