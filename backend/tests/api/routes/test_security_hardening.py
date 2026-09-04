import io
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.models import (
    User,
    UserCreate,
    UserRole,
)
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def create_security_test_user(
    db: Session,
    role: UserRole = UserRole.contributor,
    is_active: bool = True,
    is_superuser: bool = False,
    is_developer: bool = False,
) -> tuple[User, str, str]:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(
        email=email,
        password=password,
        role=role,
        is_active=is_active,
        is_superuser=is_superuser,
        is_developer=is_developer,
    )
    user = crud.create_user(session=db, user_create=user_in)
    return user, email, password


# ---------------------------------------------------------------------------
# 1. Authentication & Inactive User Security
# ---------------------------------------------------------------------------


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    _, email, password = create_security_test_user(db, is_active=False)
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "Inactive user"


def test_inactive_user_token_rejected_in_deps(client: TestClient, db: Session) -> None:
    user, email, password = create_security_test_user(db, is_active=True)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Deactivate user in database
    user.is_active = False
    db.add(user)
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/users/me", headers=headers)
    assert r.status_code == 400
    assert r.json()["detail"] == "Inactive user"


def test_invalid_jwt_token_rejected(client: TestClient) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 2. Password Change Security
# ---------------------------------------------------------------------------


def test_password_change_requires_correct_current_password(
    client: TestClient, db: Session
) -> None:
    user, email, password = create_security_test_user(db)
    from tests.utils.user import user_authentication_headers
    headers = user_authentication_headers(client=client, email=email, password=password)

    # Wrong current password
    r_wrong = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": "wrongpassword123",
            "new_password": "brandnewpassword123",
        },
    )
    assert r_wrong.status_code == 400
    assert "Incorrect password" in r_wrong.json()["detail"]

    # Same password
    r_same = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": password,
            "new_password": password,
        },
    )
    assert r_same.status_code == 400
    assert "New password cannot be the same" in r_same.json()["detail"]

    # Valid change
    r_valid = client.patch(
        f"{settings.API_V1_STR}/users/me/password",
        headers=headers,
        json={
            "current_password": password,
            "new_password": "validNewPassword123",
        },
    )
    assert r_valid.status_code == 200
    assert r_valid.json()["message"] == "Password updated successfully"


# ---------------------------------------------------------------------------
# 3. File Upload Security Hardening
# ---------------------------------------------------------------------------


def test_file_upload_rejects_unsupported_mime_types(
    client: TestClient, db: Session
) -> None:
    user, email, _ = create_security_test_user(db, role=UserRole.contributor)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Attempt uploading an executable / script MIME type
    bad_file = io.BytesIO(b"print('malicious code')")
    r = client.post(
        f"{settings.API_V1_STR}/media/upload",
        headers=headers,
        files={"file": ("malicious.py", bad_file, "text/x-python")},
    )
    assert r.status_code == 400
    assert "File type not supported" in r.json()["detail"]


def test_file_upload_normalizes_spoofed_extensions(
    client: TestClient, db: Session
) -> None:
    user, email, _ = create_security_test_user(db, role=UserRole.contributor)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # Valid JPEG MIME type with spoofed .php extension
    fake_jpeg = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb")
    r = client.post(
        f"{settings.API_V1_STR}/media/upload",
        headers=headers,
        files={"file": ("exploit.php", fake_jpeg, "image/jpeg")},
    )
    assert r.status_code == 200
    file_url = r.json()["file_url"]
    # Saved file must NOT have .php extension; it must be sanitized to .jpg
    assert not file_url.endswith(".php")
    assert file_url.endswith(".jpg") or file_url.endswith(".jpeg")

    # Clean up uploaded test artifact
    from pathlib import Path
    uploaded_file = Path(file_url.lstrip("/"))
    if uploaded_file.exists():
        uploaded_file.unlink()


def test_file_upload_rejects_empty_files(
    client: TestClient, db: Session
) -> None:
    user, email, _ = create_security_test_user(db, role=UserRole.contributor)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    empty_file = io.BytesIO(b"")
    r = client.post(
        f"{settings.API_V1_STR}/media/upload",
        headers=headers,
        files={"file": ("empty.jpg", empty_file, "image/jpeg")},
    )
    assert r.status_code == 400
    assert "Uploaded file is empty" in r.json()["detail"]


def test_file_upload_rejects_oversized_files(
    client: TestClient, db: Session
) -> None:
    user, email, _ = create_security_test_user(db, role=UserRole.contributor)
    headers = authentication_token_from_email(client=client, email=email, db=db)

    # 16 MB dummy payload
    oversized = io.BytesIO(b"0" * (16 * 1024 * 1024))
    r = client.post(
        f"{settings.API_V1_STR}/media/upload",
        headers=headers,
        files={"file": ("large.jpg", oversized, "image/jpeg")},
    )
    assert r.status_code == 413
    assert "maximum allowed limit" in r.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Input Boundary Validation
# ---------------------------------------------------------------------------


def test_input_validation_empty_comment(client: TestClient) -> None:
    # Empty body or guest name should be rejected by Pydantic schema validation
    r = client.post(
        f"{settings.API_V1_STR}/comments/",
        json={
            "article_id": str(uuid.uuid4()),
            "guest_name": "",
            "guest_email": "guest@example.com",
            "body": "",
        },
    )
    assert r.status_code == 422


def test_input_validation_invalid_contact_email(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/contact/",
        json={
            "name": "John Doe",
            "email": "not-an-email",
            "message": "Hello there",
        },
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. Security Headers
# ---------------------------------------------------------------------------


def test_security_headers_present(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/articles/")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ---------------------------------------------------------------------------
# 6. Rate Limiting Functionality
# ---------------------------------------------------------------------------


def test_rate_limiter_triggers_429(client: TestClient) -> None:
    login_rate_limiter.force_enable_in_tests = True
    login_rate_limiter.reset()

    try:
        # Perform 20 fast calls (limit is 20)
        for _ in range(20):
            client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={"username": "wrong@example.com", "password": "wrong"},
            )

        # 21st call must return 429 Too Many Requests
        r_blocked = client.post(
            f"{settings.API_V1_STR}/login/access-token",
            data={"username": "wrong@example.com", "password": "wrong"},
        )
        assert r_blocked.status_code == 429
        assert "Too many requests" in r_blocked.json()["detail"]
        assert "Retry-After" in r_blocked.headers
    finally:
        login_rate_limiter.force_enable_in_tests = False
        login_rate_limiter.reset()
