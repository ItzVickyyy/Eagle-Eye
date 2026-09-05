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
- ``S3Storage`` is a S3-compatible object-storage backend (AWS S3, Cloudflare
  R2, Backblaze B2, MinIO, ...). It uses ``boto3`` lazily so installs that
  only need the local backend do not have to pull it in.
- It is intentionally provider-agnostic: no single vendor is hard-coded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse


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


class S3Storage:
    """S3-compatible object-storage backend.

    Works with AWS S3 and any S3-compatible service (Cloudflare R2,
    Backblaze B2, MinIO, ...). The ``endpoint_url`` setting is what makes
    this generic: when it is ``None`` boto3 talks to AWS, otherwise it
    points at the vendor of choice.

    Configuration is intentionally explicit (no implicit env-var lookups
    inside the class) so the factory has full control over which secrets
    are read and so the object is easy to construct in tests.
    """

    def __init__(
        self,
        bucket: str,
        *,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        public_url_base: str | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("S3Storage requires a non-empty bucket name.")
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._access_key = access_key
        self._secret_key = secret_key
        # ``public_url_base`` lets the deployment point at a CDN/custom
        # domain in front of the bucket. Falls back to the endpoint URL.
        if public_url_base:
            self._public_url_base = public_url_base.rstrip("/")
        elif self._endpoint_url:
            self._public_url_base = self._endpoint_url
        else:
            self._public_url_base = f"https://{bucket}.s3.{region or 'us-east-1'}.amazonaws.com"
        self._client: Any | None = None

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def public_url_base(self) -> str:
        return self._public_url_base

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3  # type: ignore[import-not-found]
                from botocore.client import Config  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - exercised in envs w/o boto3
                raise RuntimeError(
                    "S3Storage requires the 'boto3' package. "
                    "Install it with `pip install boto3`."
                ) from exc
            self._client = boto3.client(
                "s3",
                region_name=self._region,
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    @staticmethod
    def _validate_key(key: str) -> str:
        if not key:
            raise ValueError("Storage key must be non-empty.")
        # Reject Windows-style absolute paths and any path with backslashes.
        if len(key) >= 2 and key[1] == ":":
            raise ValueError(f"Unsafe storage key: {key!r}")
        normalized = key.replace("\\", "/")
        while normalized.startswith("/"):
            normalized = normalized[1:]
        if not normalized:
            raise ValueError("Storage key must be non-empty.")
        for part in normalized.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError(f"Unsafe storage key: {key!r}")
        return normalized

    def _key_from_public_url(self, public_url: str) -> str:
        """Recover the object ``key`` from a previously returned public URL.

        We only accept URLs we produced (or that share our ``public_url_base``).
        Anything else is rejected to avoid deleting objects that were not
        authored by this application.
        """
        parsed = urlparse(public_url)
        base = urlparse(self._public_url_base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Not a public URL: {public_url!r}")
        if parsed.netloc != base.netloc:
            raise ValueError(
                f"public_url host {parsed.netloc!r} does not match "
                f"storage base {base.netloc!r}."
            )
        prefix = base.path.rstrip("/")
        path = parsed.path
        if prefix and path.startswith(prefix + "/"):
            key = path[len(prefix) + 1 :]
        elif prefix and path == prefix:
            key = ""
        else:
            key = path.lstrip("/")
        return self._validate_key(key)

    def save(self, key: str, content: bytes) -> str:
        normalized = self._validate_key(key)
        client = self._get_client()
        client.put_object(Bucket=self._bucket, Key=normalized, Body=content)
        return self.public_url(normalized)

    def delete(self, public_url: str) -> bool:
        normalized = self._key_from_public_url(public_url)
        client = self._get_client()
        try:
            response = client.delete_object(Bucket=self._bucket, Key=normalized)
        except Exception:
            return False
        # ``DeleteMarker`` is set when versioning + delete-marker; we treat
        # the object as removed in that case too.
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return status in (200, 204)

    def public_url(self, key: str) -> str:
        normalized = self._validate_key(key)
        return f"{self._public_url_base}/{normalized}"


def get_storage(backend: str | None = None, local_dir: str | None = None) -> StorageProtocol:
    """Build the active storage backend from configuration.

    Unknown backends raise ``ValueError`` so invalid configuration fails fast
    instead of silently falling back to local disk in production.
    """
    from app.core.config import settings

    backend = (backend or settings.MEDIA_STORAGE_BACKEND or "local").strip().lower()
    if backend == "local":
        directory = Path(local_dir or settings.MEDIA_STORAGE_LOCAL_DIR or "uploads")
        return LocalStorage(directory)
    if backend == "s3":
        bucket = settings.MEDIA_S3_BUCKET
        if not bucket:
            raise ValueError(
                "MEDIA_S3_BUCKET must be set when MEDIA_STORAGE_BACKEND='s3'."
            )
        return S3Storage(
            bucket,
            region=settings.MEDIA_S3_REGION,
            endpoint_url=settings.MEDIA_S3_ENDPOINT_URL,
            access_key=settings.MEDIA_S3_ACCESS_KEY,
            secret_key=settings.MEDIA_S3_SECRET_KEY,
            public_url_base=settings.MEDIA_S3_PUBLIC_URL_BASE,
        )
    raise ValueError(
        f"Unknown MEDIA_STORAGE_BACKEND: {backend!r}. Supported: 'local', 's3'."
    )
