from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine, delete

from app.api.deps import get_db
from app.core import db as app_db
from app.core.config import settings
from app.core.db import init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session")
def test_engine(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Engine]:
    """SQLite engine isolated to this pytest invocation's temp directory.

    Each pytest invocation gets its own tmp dir (``tmp_path_factory``
    basename includes a unique ``pytest-N`` counter), so parallel test
    runs never share an on-disk ``test.db`` and no longer race on
    ``SQLModel.metadata.create_all``.
    """
    db_dir = tmp_path_factory.mktemp("eagle_eye_db")
    engine = create_engine(
        f"sqlite:///{db_dir / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _align_middleware_engine(
    test_engine: Engine,
) -> Generator[None]:
    """Point ``app.core.db.engine`` at the test engine for the whole session.

    ``MaintenanceModeMiddleware`` opens a fresh session against the
    module-level ``app.core.db.engine`` for every non-allowlisted request.
    Without this alignment the middleware would try to reach the production
    Postgres from ``settings.DATABASE_URL`` and hang when it is unreachable.
    """
    original_engine = app_db.engine
    app_db.engine = test_engine
    try:
        yield
    finally:
        app_db.engine = original_engine


@pytest.fixture(scope="session", autouse=True)
def db(test_engine: Engine) -> Generator[Session]:
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        init_db(session)

        def get_test_db() -> Generator[Session]:
            with Session(test_engine) as test_session:
                yield test_session

        app.dependency_overrides[get_db] = get_test_db
        yield session
        statement = delete(User)
        session.execute(statement)
        session.commit()
    SQLModel.metadata.drop_all(test_engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
