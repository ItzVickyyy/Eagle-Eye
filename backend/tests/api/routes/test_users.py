import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.security import verify_password
from app.models import User, UserCreate
from tests.utils.user import create_random_user
from tests.utils.utils import random_email, random_lower_string


def test_get_users_superuser_me(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=superuser_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["is_active"] is True
    assert current_user["is_superuser"]
    assert current_user["email"] == settings.FIRST_SUPERUSER


def test_get_users_normal_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/users/me", headers=normal_user_token_headers)
    current_user = r.json()
    assert current_user
    assert current_user["is_active"] is True
    assert current_user["is_superuser"] is False
    assert current_user["email"] == settings.EMAIL_TEST_USER


def test_create_user_new_email(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    with (
        patch("app.utils.send_email", return_value=None),
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        username = random_email()
        password = random_lower_string()
        data = {"email": username, "password": password}
        r = client.post(
            f"{settings.API_V1_STR}/users/",
            headers=superuser_token_headers,
            json=data,
        )
        assert 200 <= r.status_code < 300
        created_user = r.json()
        user = crud.get_user_by_email(session=db, email=username)
        assert user
        assert user.email == created_user["email"]


def test_get_existing_user_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id
    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert 200 <= r.status_code < 300
    api_user = r.json()
    existing_user = crud.get_user_by_email(session=db, email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


def test_get_non_existing_user_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404
    assert r.json() == {"detail": "User not found"}


def test_get_existing_user_current_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id

    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=headers,
    )
    assert 200 <= r.status_code < 300
    api_user = r.json()
    existing_user = crud.get_user_by_email(session=db, email=username)
    assert existing_user
    assert existing_user.email == api_user["email"]


def test_get_existing_user_permissions_error(
    db: Session,
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    user = create_random_user(db)

    r = client.get(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json() == {"detail": "The user doesn't have enough privileges"}


def test_get_non_existing_user_permissions_error(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    user_id = uuid.uuid4()

    r = client.get(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json() == {"detail": "The user doesn't have enough privileges"}


def test_create_user_existing_username(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    # username = email
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    crud.create_user(session=db, user_create=user_in)
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=superuser_token_headers,
        json=data,
    )
    created_user = r.json()
    assert r.status_code == 400
    assert "_id" not in created_user


def test_create_user_by_normal_user(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    username = random_email()
    password = random_lower_string()
    data = {"email": username, "password": password}
    r = client.post(
        f"{settings.API_V1_STR}/users/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 403


def test_retrieve_users(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    crud.create_user(session=db, user_create=user_in)

    username2 = random_email()
    password2 = random_lower_string()
    user_in2 = UserCreate(email=username2, password=password2)
    crud.create_user(session=db, user_create=user_in2)

    r = client.get(f"{settings.API_V1_STR}/users/", headers=superuser_token_headers)
    all_users = r.json()

    assert len(all_users["data"]) > 1
    assert "count" in all_users
    for item in all_users["data"]:
        assert "email" in item


def test_update_user_me(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    full_name = "Updated Name"
    email = random_email()
    data = {"full_name": full_name, "email": email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()
    assert updated_user["email"] == email
    assert updated_user["full_name"] == full_name

    user_query = select(User).where(User.email == email)
    user_db = db.exec(user_query).first()
    assert user_db
    assert user_db.email == email
    assert user_db.full_name == full_name


def test_update_password_me(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """``PATCH /users/me/password`` rotates the password AND bumps
    ``token_version`` so every other session for that user is invalidated.

    This test acts on a dedicated user (not the module-scoped superuser)
    so the rotation does not invalidate the cached
    ``superuser_token_headers`` used by the rest of the file.
    """
    from app.crud import create_user
    from app.models import UserCreate
    from tests.utils.user import user_authentication_headers

    email = random_email()
    old_password = random_lower_string()
    new_password = random_lower_string()

    # Provision a fresh, non-superuser to act on. Using a dedicated user
    # isolates the ``token_version`` bump from the module-scoped
    # superuser's auth headers.
    create_user(
        session=db,
        user_create=UserCreate(
            email=email,
            full_name="Password Changer",
            password=old_password,
            is_active=True,
            is_superuser=False,
        ),
    )
    user_headers = user_authentication_headers(
        client=client, email=email, password=old_password
    )

    # First PATCH: rotate password. Bumps token_version internally.
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=user_headers,
        json={"current_password": old_password, "new_password": new_password},
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    # The OLD token (tv=0) is now invalid: the rotation bumped tv to 1
    # so every other session for this user is rejected.
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=user_headers,
    )
    assert r.status_code == 401

    # The user can still log in with the new password and obtain a
    # fresh token.
    fresh_headers = user_authentication_headers(
        client=client, email=email, password=new_password
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=fresh_headers,
    )
    assert r.status_code == 200
    assert r.json()["email"] == email

    # The DB row reflects the new hash.
    user_query = select(User).where(User.email == email)
    user_db = db.exec(user_query).first()
    assert user_db
    verified, _ = verify_password(new_password, user_db.hashed_password)
    assert verified


def test_update_password_me_incorrect_password(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    new_password = random_lower_string()
    data = {"current_password": new_password, "new_password": new_password}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert updated_user["detail"] == "Incorrect password"


def test_update_user_me_email_exists(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    data = {"email": user.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


def test_update_password_me_same_password_error(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {
        "current_password": settings.FIRST_SUPERUSER_PASSWORD,
        "new_password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 400
    updated_user = r.json()
    assert (
        updated_user["detail"] == "New password cannot be the same as the current one"
    )


def test_register_user(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    full_name = random_lower_string()
    data = {"email": username, "password": password, "full_name": full_name}
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 200
    created_user = r.json()
    assert created_user["email"] == username
    assert created_user["full_name"] == full_name

    user_query = select(User).where(User.email == username)
    user_db = db.exec(user_query).first()
    assert user_db
    assert user_db.email == username
    assert user_db.full_name == full_name
    verified, _ = verify_password(password, user_db.hashed_password)
    assert verified


def test_register_user_already_exists_error(client: TestClient) -> None:
    password = random_lower_string()
    full_name = random_lower_string()
    data = {
        "email": settings.FIRST_SUPERUSER,
        "password": password,
        "full_name": full_name,
    }
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=data,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "The user with this email already exists in the system"


def test_update_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 200
    updated_user = r.json()

    assert updated_user["full_name"] == "Updated_full_name"

    user_query = select(User).where(User.email == username)
    user_db = db.exec(user_query).first()
    db.refresh(user_db)
    assert user_db
    assert user_db.full_name == "Updated_full_name"


def test_update_user_not_exists(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"full_name": "Updated_full_name"}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "The user with this id does not exist in the system"


def test_update_user_email_exists(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    username2 = random_email()
    password2 = random_lower_string()
    user_in2 = UserCreate(email=username2, password=password2)
    user2 = crud.create_user(session=db, user_create=user_in2)

    data = {"email": user2.email}
    r = client.patch(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "User with this email already exists"


def test_delete_user_me(client: TestClient, db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id

    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}

    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
    )
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"
    result = db.exec(select(User).where(User.id == user_id)).first()
    assert result is None

    user_query = select(User).where(User.id == user_id)
    user_db = db.execute(user_query).first()
    assert user_db is None


def test_delete_user_me_as_superuser(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/me",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    response = r.json()
    assert response["detail"] == "Super users are not allowed to delete themselves"


def test_delete_user_super_user(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)
    user_id = user.id
    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    deleted_user = r.json()
    assert deleted_user["message"] == "User deleted successfully"
    result = db.exec(select(User).where(User.id == user_id)).first()
    assert result is None


def test_delete_user_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.delete(
        f"{settings.API_V1_STR}/users/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_delete_user_current_super_user_error(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    super_user = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert super_user
    user_id = super_user.id

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Super users are not allowed to delete themselves"


def test_delete_user_without_privileges(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    user = crud.create_user(session=db, user_create=user_in)

    r = client.delete(
        f"{settings.API_V1_STR}/users/{user.id}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "The user doesn't have enough privileges"


def test_admin_password_change_invalidates_target_user_sessions(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """``PATCH /users/{id}`` with ``password`` rotates the target user's
    password AND bumps the target's ``token_version`` so all of that
    user's existing sessions are rejected.

    The administrator's own session is NOT touched by the rotation.
    """
    from tests.utils.user import user_authentication_headers

    target_email = random_email()
    old_password = random_lower_string()
    new_password = random_lower_string()
    target = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=target_email,
            full_name="Target User",
            password=old_password,
            is_active=True,
            is_superuser=False,
        ),
    )

    # Target user logs in (simulates "device A" of the target user).
    target_headers = user_authentication_headers(
        client=client, email=target_email, password=old_password
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token", headers=target_headers
    )
    assert r.status_code == 200

    # The admin's session is valid up front.
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200

    # Admin rotates the target user's password via the admin endpoint.
    r = client.patch(
        f"{settings.API_V1_STR}/users/{target.id}",
        headers=superuser_token_headers,
        json={"password": new_password},
    )
    assert r.status_code == 200

    # Target user's pre-rotation token is now invalid (tv was bumped).
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token", headers=target_headers
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"

    # The administrator's own session is untouched.
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    assert r.status_code == 200
    assert r.json()["email"] == settings.FIRST_SUPERUSER

    # Target user can authenticate with the new password.
    fresh_target_headers = user_authentication_headers(
        client=client, email=target_email, password=new_password
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=fresh_target_headers,
    )
    assert r.status_code == 200
    assert r.json()["email"] == target_email

    # DB row reflects the new hash.
    db.refresh(target)
    verified, _ = verify_password(new_password, target.hashed_password)
    assert verified


def test_admin_password_change_does_not_invalidate_target_user_sessions_for_unrelated_updates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """``PATCH /users/{id}`` WITHOUT a ``password`` field must NOT bump
    the target user's ``token_version``. Only a password rotation is a
    security event.
    """
    from tests.utils.user import user_authentication_headers

    target_email = random_email()
    password = random_lower_string()
    target = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=target_email,
            full_name="Unrelated Update",
            password=password,
            is_active=True,
            is_superuser=False,
        ),
    )
    target_headers = user_authentication_headers(
        client=client, email=target_email, password=password
    )
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token", headers=target_headers
    )
    assert r.status_code == 200

    # Admin updates a non-credential field. The target's ``tv`` must not
    # move, so the target's existing token keeps working.
    r = client.patch(
        f"{settings.API_V1_STR}/users/{target.id}",
        headers=superuser_token_headers,
        json={"full_name": "Renamed"},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Renamed"

    r = client.post(
        f"{settings.API_V1_STR}/login/test-token", headers=target_headers
    )
    assert r.status_code == 200


def test_admin_password_change_does_not_bump_admin_token_version(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Belt-and-braces: verify the admin's ``token_version`` row is
    unchanged after a password rotation on a different user.
    """
    target_email = random_email()
    old_password = random_lower_string()
    new_password = random_lower_string()
    target = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=target_email,
            full_name="Other User",
            password=old_password,
            is_active=True,
            is_superuser=False,
        ),
    )

    admin_row = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    assert admin_row is not None
    admin_tv_before = admin_row.token_version

    r = client.patch(
        f"{settings.API_V1_STR}/users/{target.id}",
        headers=superuser_token_headers,
        json={"password": new_password},
    )
    assert r.status_code == 200

    db.refresh(admin_row)
    assert admin_row.token_version == admin_tv_before

    # And the target's tv was bumped.
    db.refresh(target)
    assert (target.token_version or 0) >= 1
