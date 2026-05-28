"""Authentication API endpoints.

Endpoints:
  POST /auth/register             — public registration
  POST /auth/register/candidate   — candidate self-registration with GDPR consent
  POST /auth/login                — login (rate-limited per IP via slowapi)
  POST /auth/refresh              — refresh access token via httpOnly cookie
  POST /auth/logout               — invalidate refresh token
  POST /auth/verify-email         — verify email with DB-backed token
  POST /auth/forgot-password      — request password reset (email enumeration-safe)
  POST /auth/reset-password       — apply password reset
"""
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.email_token import EmailToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    CandidateRegisterRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserBrief,
    VerifyEmailRequest,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_email_token,
    hash_password,
    verify_password,
)
from app.utils.email import send_password_reset_email, send_verification_email
from app.utils.logging import logger

# Limiter instance — shared with main.py via app.state.limiter
# The router uses the same Limiter key_func as main.py
_limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Per-account brute-force protection (in-memory, single-instance)
# Tracks: email -> [(attempt_timestamp), ...]
# After 5 attempts in 15 minutes, raises 429.
# ---------------------------------------------------------------------------
_login_attempts: dict[str, list[datetime]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW = timedelta(minutes=15)


def _check_account_lockout(email: str) -> None:
    """Raise 429 if too many recent login failures for this email."""
    now = datetime.now(timezone.utc)
    cutoff = now - _ATTEMPT_WINDOW
    attempts = [t for t in _login_attempts[email] if t > cutoff]
    _login_attempts[email] = attempts
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in 15 minutes.",
        )


def _record_failed_attempt(email: str) -> None:
    _login_attempts[email].append(datetime.now(timezone.utc))


def _clear_attempts(email: str) -> None:
    _login_attempts.pop(email, None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register", response_model=MessageResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    """Register a new user (any role) and send a verification email."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        role="candidate",  # public registration defaults to candidate
        display_name=body.display_name,
        email_verified=False,
    )
    db.add(user)
    await db.flush()  # get user.id without committing

    # Create email verification token
    token_str = generate_email_token()
    email_token = EmailToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token=token_str,
        token_type="verify_email",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(email_token)
    await db.commit()

    # Send verification email (best-effort)
    try:
        await send_verification_email(user.email, token_str)
    except Exception as exc:
        logger.error(f"Could not send verification email to {user.email}: {exc}")

    return MessageResponse(message="Check your email to verify your account")


@router.post("/register/candidate", response_model=MessageResponse)
async def register_candidate(
    body: CandidateRegisterRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Candidate self-registration requiring explicit GDPR consent."""
    if not body.gdpr_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GDPR consent is required to register as a candidate",
        )

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        role="candidate",
        display_name=body.display_name,
        email_verified=False,
        gdpr_consent=True,
        gdpr_consent_at=now,
    )
    db.add(user)
    await db.flush()

    token_str = generate_email_token()
    email_token = EmailToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token=token_str,
        token_type="verify_email",
        expires_at=now + timedelta(hours=24),
    )
    db.add(email_token)
    await db.commit()

    try:
        await send_verification_email(user.email, token_str)
    except Exception as exc:
        logger.error(f"Could not send verification email to {user.email}: {exc}")

    return MessageResponse(message="Check your email to verify your account")


@router.post("/login", response_model=TokenResponse)
@_limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login and receive JWT access token + httpOnly refresh cookie.

    Rate limited via slowapi (10/minute per IP) AND per-account (5 attempts/15 min).
    Note: Request must be the first positional argument for slowapi decorator.
    """
    # Per-account lockout check (in-memory)
    _check_account_lockout(body.email)

    # Look up user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        _record_failed_attempt(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    if not verify_password(body.password, user.hashed_password):
        _record_failed_attempt(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    _clear_attempts(body.email)

    # Create tokens
    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )
    jti = str(uuid.uuid4())
    refresh_jwt = create_refresh_token(user_id=str(user.id), jti=jti)

    # Store refresh token hash in DB
    token_hash = bcrypt.hashpw(jti.encode(), bcrypt.gensalt(rounds=12)).decode()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES
    )
    refresh_token_record = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_token_record)
    await db.commit()

    # Set httpOnly refresh cookie — secure flag driven by settings.COOKIE_SECURE
    response.set_cookie(
        key="refresh_token",
        value=refresh_jwt,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/auth/refresh",
    )

    return TokenResponse(
        access_token=access_token,
        user=UserBrief.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access token using the httpOnly refresh cookie."""
    refresh_jwt = request.cookies.get("refresh_token")
    if not refresh_jwt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_token(refresh_jwt)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token",
        )

    # Find matching refresh token by checking against stored hashes
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == uuid.UUID(user_id),
            RefreshToken.revoked_at.is_(None),
        )
    )
    token_records = result.scalars().all()

    matching_record = None
    for record in token_records:
        if bcrypt.checkpw(jti.encode(), record.token_hash.encode()):
            matching_record = record
            break

    if matching_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    # Compare datetimes safely: handle both timezone-aware (PostgreSQL)
    # and timezone-naive (SQLite in tests) expires_at values.
    expires_at = matching_record.expires_at
    now_utc = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        # Naive datetime from SQLite — treat as UTC
        expires_at_aware = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at_aware = expires_at
    if expires_at_aware < now_utc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Load user
    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active or not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive or unverified",
        )

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserBrief.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Invalidate the refresh token and clear the cookie."""
    refresh_jwt = request.cookies.get("refresh_token")
    if refresh_jwt:
        try:
            payload = decode_token(refresh_jwt)
            jti = payload.get("jti")
            user_id = payload.get("sub")
            if jti and user_id:
                result = await db.execute(
                    select(RefreshToken).where(
                        RefreshToken.user_id == uuid.UUID(user_id),
                        RefreshToken.revoked_at.is_(None),
                    )
                )
                token_records = result.scalars().all()
                for record in token_records:
                    if bcrypt.checkpw(jti.encode(), record.token_hash.encode()):
                        record.revoked_at = datetime.now(timezone.utc)
                        break
                await db.commit()
        except Exception:
            pass  # best-effort revocation

    response.delete_cookie(key="refresh_token", path="/auth/refresh")
    return MessageResponse(message="Logged out")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Verify a user's email using the DB-backed token."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token == body.token,
            EmailToken.token_type == "verify_email",
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
    )
    email_token = result.scalar_one_or_none()

    if email_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    # Mark user as verified
    user = await db.get(User, email_token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.email_verified = True
    email_token.used_at = now
    await db.commit()

    return MessageResponse(message="Email verified")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Request a password reset email. Always returns success to prevent email enumeration."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is not None:
        token_str = generate_email_token()
        now = datetime.now(timezone.utc)
        email_token = EmailToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token=token_str,
            token_type="reset_password",
            expires_at=now + timedelta(hours=1),
        )
        db.add(email_token)
        await db.commit()

        try:
            await send_password_reset_email(user.email, token_str)
        except Exception as exc:
            logger.error(f"Could not send reset email to {user.email}: {exc}")

    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Reset password using a time-limited DB-backed token."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailToken).where(
            EmailToken.token == body.token,
            EmailToken.token_type == "reset_password",
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
    )
    email_token = result.scalar_one_or_none()

    if email_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user = await db.get(User, email_token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update password
    user.hashed_password = hash_password(body.new_password)
    email_token.used_at = now

    # Revoke all existing refresh tokens for this user
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    for token_record in result.scalars().all():
        token_record.revoked_at = now

    await db.commit()

    return MessageResponse(message="Password reset successful")
