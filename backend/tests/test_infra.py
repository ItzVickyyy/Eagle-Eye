"""Regression tests for test-infrastructure reliability fixes.

Covers:
  * an isolated SQLite test engine per pytest invocation via
    ``tmp_path_factory`` (no more race on a shared ``backend/test.db``)
  * session-wide alignment of ``app.core.db.engine`` — the engine that
    ``MaintenanceModeMiddleware`` opens for every non-allowlisted request —
    so API tests never reach production Postgres.
"""

from pathlib import Path

from sqlalchemy import Engine

from app.core import db as app_db
from app.core.config import settings


def test_test_engine_uses_invocation_isolated_temp_db(
    test_engine: Engine,
) -> None:
    """The test engine must live under pytest's temp dir, never ``./test.db``
    in the repository working directory."""
    assert test_engine.url.database is not None
    db_path = Path(test_engine.url.database).resolve()
    assert test_engine.name == "sqlite"
    assert db_path.is_absolute()
    assert db_path.name == "test.db"
    assert db_path.parent.name.startswith("eagle_eye_db")
    assert "pytest-of-" in str(db_path)
    backend_root = Path(__file__).resolve().parents[1]
    assert backend_root not in db_path.parents


def test_middleware_engine_aligned_to_test_engine(
    test_engine: Engine,
) -> None:
    """``MaintenanceModeMiddleware`` reads ``app.core.db.engine``; it must be
    the isolated SQLite test engine for the whole session."""
    assert app_db.engine is test_engine


def test_suite_never_touches_production_postgres(
    test_engine: Engine,
) -> None:
    """Even with a Postgres ``DATABASE_URL`` in ``.env``, the engine used by
    the app under pytest (including the middleware) is SQLite."""
    assert str(settings.DATABASE_URL).startswith("postgresql")
    assert app_db.engine is test_engine
    assert test_engine.name == "sqlite"
    assert app_db.engine.name == "sqlite"
