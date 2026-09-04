"""
Storage layer for media files.

This module provides a provider-agnostic boundary between the media API and
where binary files actually live. The active backend is selected through
application configuration (``MEDIA_STORAGE_BACKEND``).

Design notes
------------
- The API router keeps all security checks (MIME, extension, size, empty-file,
  path containment, RBAC) and delegates only the physical persistence + URL
  generation to an active backend.
- ``LocalStorage`` writes to ``MEDIA_STORAGE_LOCAL_DIR`` and serves files via
  the ``/uploads`` static mount already wired in ``app.main``.
- A future object-storage backend (e.g. S3-compatible bucket, Cloudinary,
  Supabase Storage) can implement the same protocol without rewriting the
  media router. It is intentionally provider-agnostic: no single vendor is
  hard-coded here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageProtocol(Protocol):
    """Minimal persistence contract a media storage backend must satisfy."""

    def save(self, key: str, content: bytes) -> str:
        """Persist ``content`` under ``key`` and return a public URL."""
        ...

    def delete(self, public_url: str) -> bool:
        """Remove the file referenced by ``public_url`` if it exists."""
        ...

    def public_url(self, key: str) -> str:
        """Return the externally accessible URL for a stored ``key``."""
        ...


class LocalStorage:
    """Local-filesystem backend used for development / single-node setups."""

    def __init__(self, directory: Path, url_prefix: str = "/uploads") -> None:
        self._directory = Path(directory).resolve()
        # Retain the historical "--path-relative" default: the resolved dir is
        # created eagerly so uploads have a stable home regardless of CWD.
        self._directory.mkdir(parents=True, exist_ok=True)
        self._url_prefix = url_prefix.rstrip("/")

    @property
    def directory(self) -> Path:
        return self._directory

    def _resolve_safe(self, key: str) -> Path:
        target = (self._directory / key).resolve()
        if not target.is_relative_to(self._directory):
            raise ValueError(f"Unsafe storage key: {key!r}")
        return target

    def save(self, key: str, content: bytes) -> str:
        target = self._resolve_safe(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self.public_url(key)

    def delete(self, public_url: str) -> bool:
        # ``public_url`` for the local backend is always ``/uploads/<key>``.
        key = public_url.removeprefix(self._url_prefix).lstrip("/")
        target = self._resolve_safe(key)
        if not target.is_file():
            return False
        target.unlink()
        return True

    def public_url(self, key: str) -> str:
        return f"{self._url_prefix}/{key.lstrip('/')}"


def get_storage(backend: str | None = None, local_dir: str | None = None) -> StorageProtocol:
    """Build the active storage backend from configuration.

    Unknown backends raise ``ValueError`` so invalid configuration fails fast
    instead of silently falling back to local disk in production.
    """
    backend = (backend or "local").strip().lower()
    if backend == "local":
        directory = Path(local_dir or "uploads")
        return LocalStorage(directory)
    raise ValueError(
        f"Unknown MEDIA_STORAGE_BACKEND: {backend!r}. Supported: 'local'."
    )
