from unittest import mock
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate, UserRole
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import random_email, random_lower_string


def test_health_check_public(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/utils/health-check/")
    assert r.status_code == 200
    assert r.json() is True


def test_test_email_superadmin(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    with (
        mock.patch("app.api.routes.utils.send_email") as send_email_mock,
        mock.patch("app.api.routes.utils.generate_test_email") as gen_email_mock,
    ):
        gen_email_mock.return_value = Mock(
            email_to="foo@example.com",
            subject="Test",
            html_content="<p>Test</p>",
        )
        r = client.post(
            f"{settings.API_V1_STR}/utils/test-email/",
            headers=superuser_token_headers,
            params={"email_to": "foo@example.com"},
        )
    assert r.status_code == 201
    assert gen_email_mock.called
    send_email_mock.assert_called_once()
    assert send_email_mock.call_args.kwargs["email_to"] == "foo@example.com"


def test_test_email_requires_auth(client: TestClient) -> None:
    with mock.patch("app.api.routes.utils.send_email") as send_email_mock:
        r = client.post(
            f"{settings.API_V1_STR}/utils/test-email/",
            params={"email_to": "foo@example.com"},
        )
    assert r.status_code == 401
    send_email_mock.assert_not_called()


def test_test_email_forbidden_for_contributor(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email, password=password, role=UserRole.contributor
        ),
    )
    headers = authentication_token_from_email(client=client, email=email, db=db)
    with mock.patch("app.api.routes.utils.send_email") as send_email_mock:
        r = client.post(
            f"{settings.API_V1_STR}/utils/test-email/",
            headers=headers,
            params={"email_to": "foo@example.com"},
        )
    assert r.status_code == 403
    send_email_mock.assert_not_called()
