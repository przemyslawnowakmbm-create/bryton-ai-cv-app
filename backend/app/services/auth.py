"""Authentication service: password hashing, JWT creation/decoding, email token generation.

Uses bcrypt directly (NOT passlib — passlib is deprecated).
Uses PyJWT for token encoding/decoding.
"""
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt with work factor 12."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash (constant-time)."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, role: str, tenant_id: str | None) -> str:
    """Create a 15-minute JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "type": "access",
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, jti: str) -> str:
    """Create a 7-day JWT refresh token carrying jti for DB-backed invalidation."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "exp": now + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_email_token() -> str:
    """Generate a cryptographically secure URL-safe token for email verification / password reset."""
    return secrets.token_urlsafe(64)
