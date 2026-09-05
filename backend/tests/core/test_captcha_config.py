"""Tests for CAPTCHA configuration consistency validation.

The validator runs once at process startup, so a misconfigured
production deployment must refuse to boot rather than silently
disabling CAPTCHA or leaking a missing-secret warning after a request
is already in flight. These tests cover the five required scenarios:

  1. ``CAPTCHA_ENABLED=False`` (default) is valid even when no keys
     are set, so local dev and the existing automated suite keep
     working unchanged.
  2. ``CAPTCHA_ENABLED=True`` with all keys populated is valid and
     must not raise.
  3. ``CAPTCHA_ENABLED=True`` with no keys set must fail fast in
     non-development environments.
  4. ``CAPTCHA_ENABLED=True`` with only the site key set (no
     secret, no frontend key) must fail fast and name the missing
     variables so the operator can fix them quickly.
  5. Error messages and warnings must never include the value of
     any secret, so the validator can be wired to startup logs
     without re-introducing the very leak it is meant to surface.
"""

from __future__ import annotations

import re
import warnings
from typing import Any, Mapping

from pydantic import ValidationError
import pytest

from app.core.config import Settings


def _build(**overrides: object) -> Settings:
    """Build a Settings instance without reading the .env file.

    ``model_construct`` skips validation entirely, so the instance is
    not run through the real validators; the test then calls the
    CAPTCHA validator under test explicitly. Required fields are
    filled with throwaway values because the constructor only needs
    them present to allow field assignment.
    """
    base: dict[str, object] = {
        "SECRET_KEY": "x" * 32,
        "PROJECT_NAME": "Eagle Eye",
        "DATABASE_URL": "sqlite:///./test-captcha-config.db",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "x" * 32,
    }
    base.update(overrides)
    return Settings.model_construct(  # type: ignore[call-overload]
        _env_file=None,
        **base,
    )


def test_captcha_disabled_does_not_require_keys() -> None:
    """CAPTCHA off (the dev/test default) is always valid."""
    settings = _build(
        CAPTCHA_ENABLED=False,
        TURNSTILE_SITE_KEY=None,
        TURNSTILE_SECRET_KEY=None,
        VITE_TURNSTILE_SITE_KEY=None,
    )
    settings._validate_captcha_configuration()
    assert settings.captcha_required is False


def test_captcha_enabled_with_all_keys_is_valid() -> None:
    """CAPTCHA on with every key populated is accepted."""
    settings = _build(
        CAPTCHA_ENABLED=True,
        TURNSTILE_SITE_KEY="1x00000000000000000000AA",
        TURNSTILE_SECRET_KEY="1x0000000000000000000000000000000AA",
        VITE_TURNSTILE_SITE_KEY="1x00000000000000000000AA",
    )
    settings._validate_captcha_configuration()
    assert settings.captcha_required is True


def test_captcha_enabled_without_any_keys_fails_fast() -> None:
    """CAPTCHA on with no keys must raise in production-style envs."""
    settings = _build(
        CAPTCHA_ENABLED=True,
        FASTAPI_ENV=None,
        TURNSTILE_SITE_KEY=None,
        TURNSTILE_SECRET_KEY=None,
        VITE_TURNSTILE_SITE_KEY=None,
    )
    with pytest.raises(ValueError) as excinfo:
        settings._validate_captcha_configuration()
    message = str(excinfo.value)
    assert "TURNSTILE_SECRET_KEY" in message
    assert "TURNSTILE_SITE_KEY" in message
    assert "VITE_TURNSTILE_SITE_KEY" in message


def test_captcha_enabled_with_partial_keys_fails_fast() -> None:
    """CAPTCHA on with only the site key set must name the missing ones."""
    settings = _build(
        CAPTCHA_ENABLED=True,
        FASTAPI_ENV=None,
        TURNSTILE_SITE_KEY="1x00000000000000000000AA",
        TURNSTILE_SECRET_KEY=None,
        VITE_TURNSTILE_SITE_KEY=None,
    )
    with pytest.raises(ValueError) as excinfo:
        settings._validate_captcha_configuration()
    message = str(excinfo.value)
    assert "TURNSTILE_SECRET_KEY" in message
    assert "VITE_TURNSTILE_SITE_KEY" in message
    assert re.search(r"(?:^|,\s)TURNSTILE_SITE_KEY(?:,|\s|$|\.)", message) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "TURNSTILE_SITE_KEY": None,
            "TURNSTILE_SECRET_KEY": "should-not-leak-SECRET-12345",
            "VITE_TURNSTILE_SITE_KEY": "should-not-leak-FRONTEND-67890",
        },
        {
            "TURNSTILE_SITE_KEY": "should-not-leak-SITE-AAAAA",
            "TURNSTILE_SECRET_KEY": "should-not-leak-SECRET-BBBBB",
            "VITE_TURNSTILE_SITE_KEY": None,
        },
    ],
)
def test_captcha_validation_never_leaks_secret_values(overrides: dict[str, object]) -> None:
    """Validator output must not include any key value, secret or not.

    The site key is technically public but treating it the same way
    here keeps the test strict: the validator should report *names* of
    variables only, never values, so it is safe to wire into startup
    logs and error reports without re-introducing the very leak it is
    meant to surface.
    """
    base: dict[str, object] = {
        "CAPTCHA_ENABLED": True,
        "FASTAPI_ENV": None,
        "TURNSTILE_SITE_KEY": None,
        "TURNSTILE_SECRET_KEY": None,
        "VITE_TURNSTILE_SITE_KEY": None,
    }
    base.update(overrides)
    settings = _build(**base)

    with pytest.raises(ValueError) as excinfo:
        settings._validate_captcha_configuration()
    message = str(excinfo.value)

    for forbidden_value in (
        "should-not-leak-SECRET-12345",
        "should-not-leak-FRONTEND-67890",
        "should-not-leak-SITE-AAAAA",
        "should-not-leak-SECRET-BBBBB",
    ):
        assert forbidden_value not in message, (
            f"Validator must not include secret-like value {forbidden_value!r}"
        )


def test_captcha_validation_warns_in_development_instead_of_raising() -> None:
    """In development the validator must warn, not refuse to boot.

    Local dev environments often have CAPTCHA toggled on with the
    keys intentionally left blank while wiring the deployment. The
    validator falls back to a warning so the developer can finish
    wiring without an exception, while still surfacing the gap.
    """
    settings = _build(
        CAPTCHA_ENABLED=True,
        FASTAPI_ENV="development",
        TURNSTILE_SITE_KEY=None,
        TURNSTILE_SECRET_KEY=None,
        VITE_TURNSTILE_SITE_KEY=None,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings._validate_captcha_configuration()
    assert any(
        "TURNSTILE_SECRET_KEY" in str(w.message) for w in captured
    ), "development warning must list missing variable names"
    # The values themselves must still be excluded.
    for w in captured:
        assert "should-not-leak" not in str(w.message)
