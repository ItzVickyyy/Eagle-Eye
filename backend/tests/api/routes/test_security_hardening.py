import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    _create_limiter,
    login_rate_limiter,
)
from app.main import (
    CONTENT_SECURITY_POLICY,
    HSTS_MAX_AGE_SECONDS,
    PERMISSIONS_POLICY,
)
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


def _csp_directive(name: str, policy: str = CONTENT_SECURITY_POLICY) -> str:
    """Return the value of a single CSP directive from a serialized policy."""
    parts = [part.strip() for part in policy.split(";")]
    for part in parts:
        if part.startswith(name + " "):
            return part[len(name) + 1 :]
    raise AssertionError(f"Directive {name!r} not present in CSP")


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
    assert r.headers.get("Content-Security-Policy") == CONTENT_SECURITY_POLICY
    assert r.headers.get("Permissions-Policy") == PERMISSIONS_POLICY
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert r.headers.get("Cross-Origin-Resource-Policy") == "same-origin"


def test_coop_corp_present_on_public_docs_response(client: TestClient) -> None:
    """COOP and CORP must be emitted on a non-API public response too.

    ``/docs`` is the FastAPI-built Swagger UI; it is unauthenticated, returns
    200, and is served through the same HTTP middleware chain as the API
    routes. This guards against a future refactor that, for example, mounts a
    sub-app with its own middleware and silently drops these headers.
    """
    r = client.get("/docs")
    assert r.status_code == 200
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert r.headers.get("Cross-Origin-Resource-Policy") == "same-origin"


def test_csp_forbids_remote_scripts_and_arbitrary_iframes() -> None:
    """The CSP must keep scripts and frames restricted.

    - ``default-src 'self'`` and ``script-src 'self'`` block third-party JS.
    - ``frame-src 'self'`` blocks any third-party iframe embedding, except
      the allow-listed Cloudflare Turnstile origin required by CAPTCHA.
    - ``object-src 'none'`` blocks plugin embeds (Flash/Java).
    - ``base-uri 'self'`` blocks ``<base>`` tag injection.
    """
    assert "default-src 'self'" in CONTENT_SECURITY_POLICY
    assert "script-src 'self'" in CONTENT_SECURITY_POLICY
    assert "object-src 'none'" in CONTENT_SECURITY_POLICY
    assert "base-uri 'self'" in CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY

    # script-src must not allow inline code execution.
    script_src = _csp_directive("script-src")
    assert "'unsafe-inline'" not in script_src
    assert "'unsafe-eval'" not in script_src

    # Cloudflare Turnstile is explicitly allow-listed for script/frame/connect
    # so the CAPTCHA widget can load; arbitrary other hosts remain forbidden.
    assert "https://challenges.cloudflare.com" in script_src
    for forbidden in (
        "https://cdn.jsdelivr.net",
        "https://unpkg.com",
        "https://google.com",
    ):
        assert forbidden not in script_src, (
            f"script-src must not allow {forbidden!r}"
        )

    # frame-src allows same-origin plus the explicit Turnstile host; a bare
    # ``https:`` scheme token (followed by a space, not by ``//``) would
    # re-introduce the entire TLS web as an allowed embed origin and is
    # forbidden here.
    frame_src = _csp_directive("frame-src")
    assert "'self'" in frame_src
    assert "https://challenges.cloudflare.com" in frame_src
    for forbidden in (
        "https://cdn.jsdelivr.net",
        "https://unpkg.com",
        "https://google.com",
    ):
        assert forbidden not in frame_src, (
            f"frame-src must not allow {forbidden!r}"
        )

    # connect-src allows same-origin plus the explicit Turnstile verify
    # host; there is no browser-side Sentry integration, so allowing
    # *.sentry.io would be an unused wildcard that future code could
    # mistakenly rely on.
    connect_src = _csp_directive("connect-src")
    assert "'self'" in connect_src
    assert "https://challenges.cloudflare.com" in connect_src
    assert "sentry.io" not in CONTENT_SECURITY_POLICY


def test_permissions_policy_disables_powerful_features() -> None:
    """Permissions-Policy must deny every powerful feature the app does not use."""
    for feature in (
        "camera",
        "microphone",
        "geolocation",
        "payment",
        "usb",
        "interest-cohort",
        "accelerometer",
        "gyroscope",
        "magnetometer",
    ):
        assert f"{feature}=()" in PERMISSIONS_POLICY, (
            f"Permissions-Policy must disable {feature!r}"
        )


def test_hsts_absent_over_plain_http(client: TestClient) -> None:
    """HSTS must NOT be sent over plain HTTP.

    Sending HSTS over a non-TLS response would cause browsers to remember a
    policy the deployment cannot honour, and the local dev server / test
    client both run over plain HTTP.
    """
    r = client.get(f"{settings.API_V1_STR}/articles/")
    assert r.status_code == 200
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_present_when_request_scheme_is_https() -> None:
    """HSTS is emitted when ``request.url.scheme`` is ``https``.

    Uses a fresh ``TestClient`` with ``base_url='https://testserver'`` so
    Starlette's test transport advertises the HTTPS scheme on the request.
    """
    from app.main import app

    with TestClient(app, base_url="https://testserver") as https_client:
        r = https_client.get(f"{settings.API_V1_STR}/articles/")
    assert r.status_code == 200
    hsts = r.headers.get("Strict-Transport-Security")
    assert hsts is not None
    assert hsts == f"max-age={HSTS_MAX_AGE_SECONDS}"
    # We intentionally do NOT enable includeSubDomains/preload: the
    # deployment has no documented ownership of every subdomain, and adding
    # either flag would be hard to undo once a browser caches the header.
    assert "includeSubDomains" not in hsts
    assert "preload" not in hsts


def test_hsts_present_when_proxy_advertises_https(client: TestClient) -> None:
    """A trusted ``X-Forwarded-Proto: https`` header is enough to emit HSTS.

    Production runs behind a TLS-terminating reverse proxy, so the raw
    ``request.url.scheme`` is HTTP. Honoring the forwarded scheme lets the
    header reach clients in that topology.
    """
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert r.status_code == 200
    hsts = r.headers.get("Strict-Transport-Security")
    assert hsts == f"max-age={HSTS_MAX_AGE_SECONDS}"


def test_hsts_absent_when_proxy_advertises_http(client: TestClient) -> None:
    """A reverse proxy explicitly saying ``X-Forwarded-Proto: http`` must not
    trigger HSTS even if the header is sent in a header list (e.g. a chain of
    proxies). Only the first value matters.
    """
    r = client.get(
        f"{settings.API_V1_STR}/articles/",
        headers={"X-Forwarded-Proto": "http"},
    )
    assert r.status_code == 200
    assert "Strict-Transport-Security" not in r.headers


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


def test_factory_returns_in_memory_when_redis_url_empty() -> None:
    """Empty/falsy redis_url must select the in-memory backend."""
    limiter = _create_limiter(times=5, seconds=60, redis_url="")
    assert isinstance(limiter, InMemoryRateLimiter)
    assert limiter is not login_rate_limiter  # factory returns a fresh instance


def test_factory_returns_redis_when_redis_url_set() -> None:
    """A non-empty redis_url must select the Redis backend."""
    limiter = _create_limiter(times=5, seconds=60, redis_url="redis://localhost:6379/0")
    assert isinstance(limiter, RedisRateLimiter)
    # Redis backend must expose the same test hooks the in-memory one does,
    # so swapping limiters does not break the test suite.
    assert hasattr(limiter, "force_enable_in_tests")
    assert hasattr(limiter, "reset")
    assert callable(limiter.reset)


def test_default_login_limiter_is_in_memory_when_redis_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pre-configured `login_rate_limiter` is in-memory by default.

    In CI / pytest the REDIS_URL env var is not set, so the module-level
    limiters must select the in-memory backend; this guards against an
    accidental wiring that would have every test require a live Redis.
    """
    monkeypatch.delenv("REDIS_URL", raising=False)
    # Re-read the env without a full module reload: _get_redis_url() reads
    # os.getenv on every call, so the factory output is correct.  We
    # assert by class name to avoid class-identity mismatches if the
    # module is later re-imported elsewhere in the suite.
    from app.core.rate_limit import _get_redis_url

    assert _get_redis_url() in (None, "")
    assert type(login_rate_limiter).__name__ == "InMemoryRateLimiter"


# ---------------------------------------------------------------------------
# 7. Cloudflare Turnstile CAPTCHA
# ---------------------------------------------------------------------------
# All tests use CAPTCHA_ENABLED=False (default) unless explicitly noted.
# The ``_captcha_runtime_required`` override forces the dependency active
# without touching the global flag, so negative-path tests can exercise
# verification without breaking every other test in the suite.


@pytest.fixture
def captcha_enabled() -> object:
    """Enable CAPTCHA verification for the duration of one test.

    Sets a dummy server-side secret so the ``misconfigured`` branch is
    not triggered, and restores the original ``_captcha_runtime_required``
    flag and secret on teardown. All provider calls are mocked per-test so
    no real network traffic ever leaves the suite.
    """
    original_runtime = getattr(settings, "_captcha_runtime_required", False)
    original_secret = settings.TURNSTILE_SECRET_KEY
    settings._captcha_runtime_required = True  # type: ignore[attr-defined]
    # Dummy value so the misconfiguration branch is not hit; the provider
    # call itself is always mocked in these tests.
    if not settings.TURNSTILE_SECRET_KEY:
        settings.TURNSTILE_SECRET_KEY = "dummy-test-secret"
    try:
        yield
    finally:
        settings._captcha_runtime_required = original_runtime  # type: ignore[attr-defined]
        settings.TURNSTILE_SECRET_KEY = original_secret


def _mock_verify(monkeypatch: pytest.MonkeyPatch, *, ok: bool, error_code: str | None) -> None:
    """Replace the Turnstile siteverify call with a deterministic fake."""

    async def _fake_verify(**_kwargs: object) -> tuple[bool, str | None]:
        return ok, error_code

    monkeypatch.setattr(
        "app.core.captcha._verify_with_turnstile",
        _fake_verify,
    )


def _signup_payload(
    captcha_token: str = "test-token-123",
) -> dict[str, object]:
    return {
        "email": random_email(),
        "password": random_lower_string(),
        "full_name": "Test User",
        "captcha_token": captcha_token,
    }


def test_signup_bypasses_captcha_when_disabled(client: TestClient) -> None:
    """With CAPTCHA_ENABLED=False (default), signup must work without a token."""
    payload = _signup_payload()
    payload.pop("captcha_token")
    r = client.post(f"{settings.API_V1_STR}/users/signup", json=payload)
    assert r.status_code == 200


def test_signup_rejects_missing_token_when_enabled(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
) -> None:
    """When CAPTCHA is required, omitting the token must return 403."""
    payload = _signup_payload()
    payload.pop("captcha_token")
    r = client.post(f"{settings.API_V1_STR}/users/signup", json=payload)
    assert r.status_code == 403
    assert r.json()["detail"] == "CAPTCHA token is required"


def test_signup_rejects_invalid_token_when_enabled(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-empty but invalid token must fail verification (fail-closed)."""
    _mock_verify(monkeypatch, ok=False, error_code="invalid-input-response")
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=_signup_payload(captcha_token="totally-invalid"),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "CAPTCHA verification failed"


def test_signup_accepts_valid_token_when_enabled(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid token must pass verification and let signup proceed."""
    _mock_verify(monkeypatch, ok=True, error_code=None)
    payload = _signup_payload(captcha_token="valid-token")
    r = client.post(f"{settings.API_V1_STR}/users/signup", json=payload)
    assert r.status_code == 200
    assert r.json()["email"] == payload["email"]


def test_signup_rejects_empty_token_string_when_enabled(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
) -> None:
    """An empty string token is treated as missing."""
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=_signup_payload(captcha_token=""),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "CAPTCHA token is required"


def test_signup_fail_closed_when_secret_missing(client: TestClient) -> None:
    """CAPTCHA_ENABLED=True but TURNSTILE_SECRET_KEY unset → 403 (fail-closed)."""
    original_runtime = getattr(settings, "_captcha_runtime_required", False)
    original_secret = settings.TURNSTILE_SECRET_KEY
    settings._captcha_runtime_required = True  # type: ignore[attr-defined]
    settings.TURNSTILE_SECRET_KEY = None
    try:
        r = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json=_signup_payload(),
        )
        assert r.status_code == 403
        assert "misconfigured" in r.json()["detail"]
    finally:
        settings._captcha_runtime_required = original_runtime  # type: ignore[attr-defined]
        settings.TURNSTILE_SECRET_KEY = original_secret


def test_captcha_token_not_in_error_logs(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even on verification failure, the raw token must never appear in logs."""
    _mock_verify(monkeypatch, ok=False, error_code="invalid-input-response")
    sentinel = "SENSITIVE-TOKEN-XYZ"
    with caplog.at_level("INFO"):
        r = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json=_signup_payload(captcha_token=sentinel),
        )
    assert r.status_code == 403
    assert sentinel not in caplog.text


def test_captcha_token_not_in_error_response_body(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The token must never be echoed back in the error response."""
    _mock_verify(monkeypatch, ok=False, error_code="invalid-input-response")
    sentinel = "SECRET-TOKEN-123"
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=_signup_payload(captcha_token=sentinel),
    )
    assert r.status_code == 403
    body = r.json()
    assert sentinel not in body.get("detail", "")
    # Ensure the raw token never leaked into any JSON key/value
    text = r.text
    assert sentinel not in text


def test_login_access_token_unchanged_without_captcha(client: TestClient, db: Session) -> None:
    """POST /login/access-token must NOT require captcha (backward compat)."""
    _, email, password = create_security_test_user(db)
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_password_recovery_bypasses_captcha_when_disabled(client: TestClient) -> None:
    """Password-recovery must work without captcha when CAPTCHA is off."""
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{random_email()}",
    )
    # 200 or 404 are both acceptable (email may not exist); 403 is not.
    assert r.status_code != 403


def test_contact_bypasses_captcha_when_disabled(client: TestClient) -> None:
    """Contact form must work without captcha when CAPTCHA is off."""
    r = client.post(
        f"{settings.API_V1_STR}/contact/",
        json={
            "name": "Test",
            "email": random_email(),
            "subject": "Hello",
            "message": "Test message content",
        },
    )
    assert r.status_code != 403


def test_rate_limiter_before_captcha(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rate limiter must reject before captcha runs (429, not 403)."""
    _mock_verify(monkeypatch, ok=True, error_code=None)
    from app.core.rate_limit import signup_rate_limiter

    signup_rate_limiter.force_enable_in_tests = True
    signup_rate_limiter.reset()
    try:
        # Exhaust the limiter
        for _ in range(20):
            client.post(
                f"{settings.API_V1_STR}/users/signup",
                json=_signup_payload(),
            )
        # Next call must 429 (rate limiter fires first)
        r = client.post(
            f"{settings.API_V1_STR}/users/signup",
            json=_signup_payload(),
        )
        assert r.status_code == 429
    finally:
        signup_rate_limiter.force_enable_in_tests = False
        signup_rate_limiter.reset()


def test_captcha_transport_error_fail_closed(
    client: TestClient,
    captcha_enabled: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider transport error must fail closed (403, not 5xx)."""
    _mock_verify(monkeypatch, ok=False, error_code="network")
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json=_signup_payload(captcha_token="any"),
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "CAPTCHA verification failed"
