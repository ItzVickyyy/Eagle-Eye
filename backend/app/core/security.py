from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta,
    *,
    token_version: int = 0,
    jti: str | None = None,
) -> str:
    """Create a signed access token carrying ``sub``, ``exp``, ``jti``, ``tv``.

    ``jti`` (JWT ID) is a per-token unique identifier used for per-session
    revocation. ``tv`` (token version) is the issuing user's
    ``User.token_version`` and is checked on every request; rotating it
    invalidates every token issued to that user.
    """
    expire = datetime.now(UTC) + expires_delta
    to_encode: dict[str, Any] = {
        "exp": expire,
        "sub": str(subject),
        "jti": jti or uuid4().hex,
        "tv": int(token_version),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token_exp(token: str) -> datetime:
    """Return the ``exp`` claim of a JWT without verifying the signature.

    Used to compute the row expiry for a revocation entry. Only consumed on
    the same thread that just produced the token, so an unsigned parse is
    safe here.
    """
    payload = jwt.decode(token, options={"verify_signature": False})
    return datetime.fromtimestamp(int(payload["exp"]), tz=UTC)


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)
