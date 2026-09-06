"""End-to-end tests for the JWT revocation layer.

Coverage:

* ``POST /auth/logout`` adds the current ``jti`` to the denylist; the same
  bearer is rejected on subsequent requests.
* Logout is per-session: a second device's token for the same user keeps
  working.
* ``PATCH /users/me/password`` bumps ``token_version`` and invalidates
  every other session for the user.
* ``/reset-password`` does the same (covered in
  ``tests/api/routes/test_login.py::test_reset_password_invalidates_all_sessions``).
* Legacy tokens without a ``tv`` claim are rejected.
* ``is_token_revoked`` filters by ``expires_at`` so stale rows never
  cause false rejections.
* ``prune_revocations`` deletes only the rows whose ``expires_at`` is
  in the past.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token
from app.core.token_store import (
    bump_token_version,
    is_token_revoked,
    prune_revocations,
    revoke_token,
)
from app.models import TokenRevocation, User
from app.utils import generate_password_reset_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


# ----------------------------------------------------------------------- #
# /auth/logout                                                             #
# ----------------------------------------------------------------------- #


def test_logout_revokes_current_token(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    from app.crud import create_user
    from app.models import UserCreate

    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Logout User",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    headers = user_authentication_headers(client=client, email=email, password=password)

    # Token is valid before logout.
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 200

    # Logout.
    r = client.post(f"{settings.API_V1_STR}/auth/logout", headers=headers)
    assert r.status_code == 204

    # The same bearer is now rejected.
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"


def test_logout_only_invalidates_one_session(
    client: TestClient, db: Session
) -> None:
    """Logging out device A must not affect device B."""
    email = random_email()
    password = random_lower_string()
    from app.crud import create_user
    from app.models import UserCreate

    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Multi-Device",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    device_a = user_authentication_headers(
        client=client, email=email, password=password
    )
    device_b = user_authentication_headers(
        client=client, email=email, password=password
    )

    r = client.post(f"{settings.API_V1_STR}/auth/logout", headers=device_a)
    assert r.status_code == 204

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=device_a)
    assert r.status_code == 401

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=device_b)
    assert r.status_code == 200


def test_logout_without_token_is_401(client: TestClient) -> None:
    r = client.post(f"{settings.API_V1_STR}/auth/logout")
    assert r.status_code == 401


# ----------------------------------------------------------------------- #
# /users/me/password bumps token_version                                   #
# ----------------------------------------------------------------------- #


def test_password_change_invalidates_other_sessions(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()
    from app.crud import create_user
    from app.models import UserCreate

    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Password Rotation",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    headers_a = user_authentication_headers(
        client=client, email=email, password=password
    )
    headers_b = user_authentication_headers(
        client=client, email=email, password=password
    )

    # Both tokens are valid initially.
    assert (
        client.post(
            f"{settings.API_V1_STR}/login/test-token", headers=headers_a
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{settings.API_V1_STR}/login/test-token", headers=headers_b
        ).status_code
        == 200
    )

    # The current request's own token is still valid for the rotation
    # (the dep runs before the mutation), but every OTHER token is
    # killed by the ``token_version`` bump.
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers_a,
        json={"current_password": password, "new_password": new_password},
    )
    assert r.status_code == 200

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers_b)
    assert r.status_code == 401

    # The user can log in with the new password.
    fresh = user_authentication_headers(
        client=client, email=email, password=new_password
    )
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=fresh)
    assert r.status_code == 200


# ----------------------------------------------------------------------- #
# /reset-password bumps token_version                                     #
# ----------------------------------------------------------------------- #


def test_reset_password_invalidates_all_sessions(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()
    from app.crud import create_user
    from app.models import UserCreate

    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Reset User",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    headers = user_authentication_headers(
        client=client, email=email, password=password
    )
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 200

    token = generate_password_reset_token(email=email)
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        json={"token": token, "new_password": new_password},
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    # The pre-reset token is now invalid: the bump killed it.
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 401

    # The user can log in with the new password.
    fresh = user_authentication_headers(
        client=client, email=email, password=new_password
    )
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=fresh)
    assert r.status_code == 200


# ----------------------------------------------------------------------- #
# Token format & legacy tokens                                             #
# ----------------------------------------------------------------------- #


def test_legacy_token_without_tv_is_rejected(
    client: TestClient, db: Session
) -> None:
    """Tokens minted before the revocation feature (no ``tv`` claim) are
    rejected outright. The alternative — silently treating missing ``tv``
    as 0 — would let every historical token survive a password rotation.
    """
    user = db.exec(select(User)).first()
    assert user is not None

    legacy = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {legacy}"},
    )
    assert r.status_code == 401


# ----------------------------------------------------------------------- #
# token_store unit tests                                                   #
# ----------------------------------------------------------------------- #


def _make_user(db: Session) -> User:
    email = random_email()
    from app.crud import create_user
    from app.models import UserCreate

    return create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Store Tester",
            password=random_lower_string(),
            is_active=True,
            is_superuser=False,
        ),
    )


def test_revoke_token_is_idempotent(db: Session) -> None:
    user = _make_user(db)
    jti = uuid4().hex
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    revoke_token(
        session=db, jti=jti, user_id=user.id, expires_at=expires_at
    )
    db.commit()
    revoke_token(
        session=db, jti=jti, user_id=user.id, expires_at=expires_at
    )
    db.commit()
    # Only one row, not two.
    rows = db.exec(select(TokenRevocation).where(TokenRevocation.jti == jti)).all()
    assert len(rows) == 1


def test_is_token_revoked_filters_by_expiry(db: Session) -> None:
    user = _make_user(db)
    jti = uuid4().hex
    # An entry that is ALREADY expired should be ignored by the hot
    # path even before ``prune_revocations`` runs.
    revoke_token(
        session=db,
        jti=jti,
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.commit()
    assert is_token_revoked(db, jti) is False


def test_bump_token_version_invalidates_older_token(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    from app.crud import create_user
    from app.models import UserCreate

    user = create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Bump Tester",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    headers = user_authentication_headers(
        client=client, email=email, password=password
    )
    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 200

    db.refresh(user)
    bump_token_version(session=db, user=user)
    db.commit()
    db.refresh(user)

    r = client.post(f"{settings.API_V1_STR}/login/test-token", headers=headers)
    assert r.status_code == 401


def test_prune_revocations_removes_only_expired_rows(db: Session) -> None:
    user = _make_user(db)
    stale_jti = uuid4().hex
    live_jti = uuid4().hex
    revoke_token(
        session=db,
        jti=stale_jti,
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    revoke_token(
        session=db,
        jti=live_jti,
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    db.commit()

    prune_revocations(db)

    remaining = db.exec(select(TokenRevocation)).all()
    remaining_jtis = {row.jti for row in remaining}
    assert live_jti in remaining_jtis
    assert stale_jti not in remaining_jtis


def test_create_access_token_contains_jti_and_tv(db: Session) -> None:
    user = _make_user(db)
    user.token_version = 7
    db.add(user)
    db.commit()

    token = create_access_token(
        user.id,
        expires_delta=timedelta(minutes=5),
        token_version=user.token_version,
    )
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[ALGORITHM]
    )
    assert payload["tv"] == 7
    assert isinstance(payload["jti"], str) and len(payload["jti"]) > 0
    assert payload["sub"] == str(user.id)
