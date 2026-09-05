import warnings
from typing import Literal, Self

from pydantic import (
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    FASTAPI_ENV: Literal["development"] | None = None

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    # Media storage
    # - "local" uses the local filesystem at MEDIA_STORAGE_LOCAL_DIR.
    # - "s3" uses an S3-compatible bucket (AWS S3, Cloudflare R2,
    #   Backblaze B2, MinIO, ...). The router is unchanged either way.
    MEDIA_STORAGE_BACKEND: Literal["local", "s3"] = "local"
    MEDIA_STORAGE_LOCAL_DIR: str = "uploads"

    # S3-compatible backend (used when MEDIA_STORAGE_BACKEND=s3).
    MEDIA_S3_BUCKET: str | None = None
    MEDIA_S3_REGION: str | None = None
    # Override the AWS endpoint (required for R2 / B2 / MinIO; leave empty for AWS).
    MEDIA_S3_ENDPOINT_URL: str | None = None
    MEDIA_S3_ACCESS_KEY: str | None = None
    MEDIA_S3_SECRET_KEY: str | None = None
    # Optional CDN/custom domain in front of the bucket. Falls back to the
    # endpoint URL (or the regional AWS hostname) when unset.
    MEDIA_S3_PUBLIC_URL_BASE: str | None = None

    # Upload size limits per media kind. Enforced by the media router.
    MAX_UPLOAD_BYTES_IMAGE: int = 15 * 1024 * 1024  # 15 MiB
    MAX_UPLOAD_BYTES_VIDEO: int = 100 * 1024 * 1024  # 100 MiB

    # Redis (optional). When set, rate limiting uses a Redis-backed sliding
    # window shared across all backend workers. When unset, each worker
    # enforces an independent in-memory limit (legacy behavior). See
    # backend/app/core/rate_limit.py for the fail-open fallback rules.
    REDIS_URL: str | None = None

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.FASTAPI_ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        if not str(self.DATABASE_URL).startswith("sqlite"):
            try:
                from pydantic import PostgresDsn
                pg_dsn = PostgresDsn(str(self.DATABASE_URL))
                for host in pg_dsn.hosts():
                    self._check_default_secret("DATABASE_URL password", host.get("password"))
            except Exception:
                pass
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore # ty: ignore[unused-ignore-comment]
