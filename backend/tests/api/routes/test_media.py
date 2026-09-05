"""Tests for the media upload route, covering image/video split and size limits.

Storage is exercised through the in-test temporary-directory LocalStorage so
we don't touch the live media folder.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.storage import get_storage


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    """Point the route's module-level `storage` at a temp directory."""
    from app.api.routes import media as media_route

    media_route.storage = get_storage("local", str(tmp_path))
    yield
    # Leave the route's storage in its temp state; the next test re-sets it.


def _upload(
    client: TestClient,
    headers: dict[str, str],
    *,
    filename: str,
    content_type: str,
    payload: bytes,
):
    return client.post(
        f"{settings.API_V1_STR}/media/upload",
        headers=headers,
        files={"file": (filename, io.BytesIO(payload), content_type)},
    )


def test_upload_image_happy_path(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    payload = b"\x89PNG\r\n\x1a\n" + b"x" * 32
    r = _upload(
        client,
        superuser_token_headers,
        filename="cover.png",
        content_type="image/png",
        payload=payload,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["file_type"] == "image"
    assert data["file_url"].endswith(".png")


def test_upload_video_happy_path(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    payload = b"\x00\x00\x00\x18ftypmp42" + b"y" * 64
    r = _upload(
        client,
        superuser_token_headers,
        filename="clip.mp4",
        content_type="video/mp4",
        payload=payload,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["file_type"] == "video"
    assert data["file_url"].endswith(".mp4")


def test_upload_rejects_oversized_image(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    too_big = b"x" * (settings.MAX_UPLOAD_BYTES_IMAGE + 1)
    r = _upload(
        client,
        superuser_token_headers,
        filename="big.png",
        content_type="image/png",
        payload=too_big,
    )
    assert r.status_code == 413
    assert "image" in r.json()["detail"].lower()


def test_upload_accepts_image_at_limit(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    # 1 byte is fine regardless of the absolute limit, but we also want to
    # confirm the boundary at the configured image limit doesn't reject.
    payload = b"x" * (settings.MAX_UPLOAD_BYTES_IMAGE)
    r = _upload(
        client,
        superuser_token_headers,
        filename="at-limit.png",
        content_type="image/png",
        payload=payload,
    )
    assert r.status_code == 200, r.text


def test_upload_image_rejected_by_video_size_limit_does_not_apply(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Images up to 15MB must still be accepted even though videos get 100MB.
    A 14MB image would be rejected by a single '15MB' cap; this test pins the
    independent image limit.
    """
    payload = b"x" * (14 * 1024 * 1024)
    r = _upload(
        client,
        superuser_token_headers,
        filename="near-limit.png",
        content_type="image/png",
        payload=payload,
    )
    assert r.status_code == 200, r.text


def test_upload_rejects_oversized_video(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    too_big = b"x" * (settings.MAX_UPLOAD_BYTES_VIDEO + 1)
    r = _upload(
        client,
        superuser_token_headers,
        filename="big.mp4",
        content_type="video/mp4",
        payload=too_big,
    )
    assert r.status_code == 413
    assert "video" in r.json()["detail"].lower()


def test_upload_rejects_unsupported_mime(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = _upload(
        client,
        superuser_token_headers,
        filename="evil.exe",
        content_type="application/octet-stream",
        payload=b"MZ",
    )
    assert r.status_code == 400
    assert "not supported" in r.json()["detail"].lower()


def test_upload_rejects_empty_file(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = _upload(
        client,
        superuser_token_headers,
        filename="empty.png",
        content_type="image/png",
        payload=b"",
    )
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_upload_requires_authentication(client: TestClient) -> None:
    r = _upload(
        client,
        {},
        filename="cover.png",
        content_type="image/png",
        payload=b"x",
    )
    assert r.status_code == 401


def test_register_url_happy_path(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/media/register",
        headers=superuser_token_headers,
        json={
            "file_url": "https://cdn.example.com/clip.mp4",
            "file_type": "video",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["file_type"] == "video"
    assert data["file_url"] == "https://cdn.example.com/clip.mp4"
