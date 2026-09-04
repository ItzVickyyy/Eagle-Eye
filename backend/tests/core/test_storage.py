import tempfile
from pathlib import Path

import pytest

from app.core.storage import LocalStorage, get_storage


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