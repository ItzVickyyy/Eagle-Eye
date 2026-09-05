import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.core.storage import LocalStorage, S3Storage, get_storage


def test_local_storage_saves_and_roundtrips_content() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStorage(Path(tmp), url_prefix="/uploads")
        url = store.save("abc123.jpg", b"image-bytes")
        assert url == "/uploads/abc123.jpg"
        saved = Path(tmp) / "abc123.jpg"
        assert saved.is_file()
        assert saved.read_bytes() == b"image-bytes"


def test_local_storage_public_url_matches_key() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStorage(Path(tmp))
        assert store.public_url("sub/dir/x.png") == "/uploads/sub/dir/x.png"
        assert store.public_url("/leading/slash.jpg") == "/uploads/leading/slash.jpg"


def test_local_storage_delete_removes_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStorage(Path(tmp))
        url = store.save("file.webp", b"webp-bytes")
        assert (Path(tmp) / "file.webp").exists()
        assert store.delete(url) is True
        assert not (Path(tmp) / "file.webp").exists()
        # Deleting a non-existent file reports False without error.
        assert store.delete(url) is False


def test_local_storage_rejects_escaping_keys() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalStorage(Path(tmp))
        with pytest.raises(ValueError):
            store.save("../escape.bin", b"bad")


def test_get_storage_selects_local_backend() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = get_storage("local", tmp)
        assert isinstance(store, LocalStorage)
        url = store.save("k.bin", b"data")
        assert (Path(tmp) / "k.bin").read_bytes() == b"data"
        assert store.delete(url) is True


def test_get_storage_fails_safely_on_unknown_backend() -> None:
    with pytest.raises(ValueError):
        get_storage("S3-mystery-vendor")


def test_s3_storage_requires_bucket_name() -> None:
    with pytest.raises(ValueError):
        S3Storage("")


def test_s3_storage_validates_keys() -> None:
    store = S3Storage(
        "bucket",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
    )
    with pytest.raises(ValueError):
        store._validate_key("")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        store._validate_key("../escape.mp4")
    with pytest.raises(ValueError):
        store._validate_key("a/../b.mp4")
    with pytest.raises(ValueError):
        store._validate_key("C:\\\\Windows\\\\file.mp4")
    # Leading slashes are normalized, not rejected — S3 keys are relative.
    assert store._validate_key("media/foo.mp4") == "media/foo.mp4"
    assert store._validate_key("/media/foo.mp4") == "media/foo.mp4"
    # Sibling path components are accepted; only ".." as a whole segment
    # is rejected.
    assert store._validate_key("a.b/..foo/c.mp4") == "a.b/..foo/c.mp4"


def test_s3_storage_public_url_uses_endpoint() -> None:
    store = S3Storage(
        "my-bucket",
        region="auto",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
    )
    assert store.public_url_base == "https://x.r2.cloudflarestorage.com"
    assert (
        store.public_url("media/foo.mp4")
        == "https://x.r2.cloudflarestorage.com/media/foo.mp4"
    )


def test_s3_storage_public_url_respects_cdn_base() -> None:
    store = S3Storage(
        "my-bucket",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
        public_url_base="https://media.example.com/cdn",
    )
    assert store.public_url_base == "https://media.example.com/cdn"
    assert (
        store.public_url("media/foo.mp4")
        == "https://media.example.com/cdn/media/foo.mp4"
    )
    # Round-trip delete: the URL we hand out must decode back to the key.
    assert (
        store._key_from_public_url("https://media.example.com/cdn/media/foo.mp4")
        == "media/foo.mp4"
    )


def test_s3_storage_rejects_foreign_host_on_delete() -> None:
    store = S3Storage(
        "bucket",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
    )
    with pytest.raises(ValueError):
        store._key_from_public_url("https://attacker.example/media/foo.mp4")


class _FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.next_delete_response: dict[str, Any] = {
            "ResponseMetadata": {"HTTPStatusCode": 204}
        }

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self.put_calls.append(kwargs)
        return {}

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        self.delete_calls.append(kwargs)
        return self.next_delete_response


def test_s3_storage_save_and_delete_roundtrip() -> None:
    store = S3Storage(
        "bucket",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
    )
    fake = _FakeS3Client()
    store._client = fake

    url = store.save("media/foo.mp4", b"video-bytes")
    assert url == "https://x.r2.cloudflarestorage.com/media/foo.mp4"
    assert len(fake.put_calls) == 1
    assert fake.put_calls[0]["Bucket"] == "bucket"
    assert fake.put_calls[0]["Key"] == "media/foo.mp4"
    assert fake.put_calls[0]["Body"] == b"video-bytes"

    assert store.delete(url) is True
    assert len(fake.delete_calls) == 1
    assert fake.delete_calls[0]["Key"] == "media/foo.mp4"


def test_s3_storage_save_uses_lazy_boto3(monkeypatch: pytest.MonkeyPatch) -> None:
    """When boto3 is missing, the constructor must still succeed and
    the error must surface only on first I/O (not on import)."""
    import builtins

    real_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "boto3" or name.startswith("boto3."):
            raise ImportError("simulated missing boto3")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    store = S3Storage("bucket", access_key="a", secret_key="b")
    with pytest.raises(RuntimeError, match="boto3"):
        store.save("k", b"data")


def test_s3_storage_save_strips_leading_slash() -> None:
    store = S3Storage(
        "bucket",
        endpoint_url="https://x.r2.cloudflarestorage.com",
        access_key="a",
        secret_key="b",
    )
    fake = _FakeS3Client()
    store._client = fake
    url = store.save("/media/foo.mp4", b"v")
    assert url == "https://x.r2.cloudflarestorage.com/media/foo.mp4"
    assert fake.put_calls[0]["Key"] == "media/foo.mp4"
