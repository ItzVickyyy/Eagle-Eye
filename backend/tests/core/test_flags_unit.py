from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.core.flags import (
    _MAINTENANCE_ALLOWLIST_PREFIXES,
    FLAG_ALLOW_PUBLIC_SIGNUP,
    FLAG_CONTACT_FORM_ENABLED,
    FLAG_MAINTENANCE_MODE,
    FLAG_PUBLIC_COMMENTS_ENABLED,
    _is_allowed_in_maintenance,
    is_maintenance_active,
    read_flag,
)
from app.models import SiteSetting

# ---------------------------------------------------------------------------
# read_flag
# ---------------------------------------------------------------------------

class TestReadFlag:
    def test_missing_returns_default(self, db: Session) -> None:
        assert read_flag(db, "nonexistent_flag", False) is False
        assert read_flag(db, "nonexistent_flag", True) is True

    def test_truthy_values(self, db: Session) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", " Yes "):
            key = f"flag_test_{val.strip()}"
            db.add(SiteSetting(key=key, value=val))
            db.commit()
            assert read_flag(db, key, False) is True
            db.delete(db.get(SiteSetting, key))
            db.commit()

    def test_falsy_values(self, db: Session) -> None:
        for val in ("false", "False", "0", "no", "off", "anything"):
            key = f"flag_test_{val}"
            db.add(SiteSetting(key=key, value=val))
            db.commit()
            assert read_flag(db, key, True) is False
            db.delete(db.get(SiteSetting, key))
            db.commit()

    def test_null_value_returns_default(self, db: Session) -> None:
        mock_setting = MagicMock(spec=SiteSetting)
        mock_setting.value = None
        with patch.object(Session, "get", return_value=mock_setting):
            assert read_flag(db, "some_key", True) is True

    def test_db_error_returns_default(self, db: Session) -> None:
        with patch.object(Session, "get", side_effect=RuntimeError("db down")):
            assert read_flag(db, "some_key", False) is False


# ---------------------------------------------------------------------------
# _is_allowed_in_maintenance
# ---------------------------------------------------------------------------

class TestIsAllowedInMaintenance:
    def test_exact_match_root(self) -> None:
        assert _is_allowed_in_maintenance("/") is True

    def test_exact_match_empty(self) -> None:
        assert _is_allowed_in_maintenance("") is True

    def test_exact_match_docs(self) -> None:
        assert _is_allowed_in_maintenance("/docs") is True
        assert _is_allowed_in_maintenance("/redoc") is True

    def test_prefix_match(self) -> None:
        assert _is_allowed_in_maintenance("/api/v1/login/token") is True
        assert _is_allowed_in_maintenance("/api/v1/developer/settings") is True
        assert _is_allowed_in_maintenance("/api/v1/settings/some_key") is True

    def test_uploads_assets(self) -> None:
        # "/uploads/" and "/assets/" are prefix entries (ending in "/"),
        # so all descendant paths are allowed during maintenance.
        assert _is_allowed_in_maintenance("/uploads/") is True
        assert _is_allowed_in_maintenance("/uploads/photo.jpg") is True
        assert _is_allowed_in_maintenance("/uploads/nested/deep/img.png") is True
        assert _is_allowed_in_maintenance("/assets/") is True
        assert _is_allowed_in_maintenance("/assets/main.js") is True
        assert _is_allowed_in_maintenance("/assets/css/app.css") is True
        assert _is_allowed_in_maintenance("/favicon.ico") is True
        # Prefix boundary: similar-looking paths must remain blocked.
        assert _is_allowed_in_maintenance("/uploads-evil/file") is False
        assert _is_allowed_in_maintenance("/assets-evil/file") is False
        # Unrelated paths remain blocked.
        assert _is_allowed_in_maintenance("/admin") is False

    def test_blocked_paths(self) -> None:
        assert _is_allowed_in_maintenance("/api/v1/articles/") is False
        assert _is_allowed_in_maintenance("/api/v1/contact/") is False
        assert _is_allowed_in_maintenance("/some/random/path") is False

    def test_trailing_slash_prefix_only(self) -> None:
        assert _is_allowed_in_maintenance("/api/v1/openapi.jsonx") is False


# ---------------------------------------------------------------------------
# is_maintenance_active
# ---------------------------------------------------------------------------

class TestIsActiveMaintenance:
    def test_delegates_to_read_flag(self, db: Session) -> None:
        existing = db.get(SiteSetting, FLAG_MAINTENANCE_MODE)
        if existing:
            existing.value = "true"
        else:
            db.add(SiteSetting(key=FLAG_MAINTENANCE_MODE, value="true"))
        db.commit()
        assert is_maintenance_active(db) is True
        # Clean up so test_default_false in the same session-scoped DB isn't contaminated
        setting = db.get(SiteSetting, FLAG_MAINTENANCE_MODE)
        if setting:
            db.delete(setting)
            db.commit()
            db.expire_all()

    def test_default_false(self, db: Session) -> None:
        assert is_maintenance_active(db) is False


# ---------------------------------------------------------------------------
# Flag constants
# ---------------------------------------------------------------------------

class TestFlagConstants:
    def test_all_constants_defined(self) -> None:
        assert FLAG_MAINTENANCE_MODE == "dev_maintenance_mode"
        assert FLAG_PUBLIC_COMMENTS_ENABLED == "dev_public_comments_enabled"
        assert FLAG_CONTACT_FORM_ENABLED == "dev_contact_form_enabled"
        assert FLAG_ALLOW_PUBLIC_SIGNUP == "dev_allow_public_signup"

    def test_allowlist_is_tuple(self) -> None:
        assert isinstance(_MAINTENANCE_ALLOWLIST_PREFIXES, tuple)
        assert len(_MAINTENANCE_ALLOWLIST_PREFIXES) > 0
