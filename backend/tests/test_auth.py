"""Auth endpoint tests.

Tests use SQLite in-memory — no PostgreSQL required.
RLS (SET LOCAL) is tested separately in Plan 02 with a real PostgreSQL testcontainer.
These tests verify the HTTP contract: status codes, response shapes, cookie handling, and auth logic.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_token import EmailToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth import hash_password

# Default test credentials — not real passwords, used only in unit tests
_TEST_PASS = "T3stPassw0rd"
_TEST_EMAIL = "alice@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(
    client: AsyncClient,
    email: str,
    password: str | None = None,
    display_name: str | None = None,
):
    """Register a user and return the response."""
    return await client.post(
        "/api/auth/register",
        json={"email": email, "password": password or _TEST_PASS, "display_name": display_name},
    )


async def _get_verification_token(db: AsyncSession, email: str) -> str | None:
    """Fetch the most recent verify_email token for a user from the DB."""
    from sqlalchemy import select

    result = await db.execute(
        select(EmailToken)
        .join(User, User.id == EmailToken.user_id)
        .where(User.email == email, EmailToken.token_type == "verify_email")
        .order_by(EmailToken.expires_at.desc())
    )
    token_record = result.scalar_one_or_none()
    return token_record.token if token_record else None


async def _verify_user(client: AsyncClient, db: AsyncSession, email: str) -> None:
    """Verify a user's email by fetching the token from DB and POSTing to verify-email."""
    token = await _get_verification_token(db, email)
    assert token is not None, f"No verification token found for {email}"
    resp = await client.post("/api/auth/verify-email", json={"token": token})
    assert resp.status_code == 200, f"verify-email failed: {resp.text}"


async def _set_email_verified(db: AsyncSession, email: str) -> None:
    """Directly mark a user's email as verified in the test DB."""
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    user.email_verified = True
    await db.commit()


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    """POST /api/auth/register with valid data returns 200 and creates unverified user."""
    resp = await _register(client, "alice@example.com")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert "verify" in data["message"].lower() or "email" in data["message"].lower()

    # Confirm user exists in DB with email_verified=False
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email_verified is False


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering the same email twice returns 409."""
    await _register(client, "bob@example.com")
    resp = await _register(client, "bob@example.com")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Registering with a password shorter than 8 chars returns 422."""
    resp = await client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_candidate_with_gdpr(client: AsyncClient, db_session: AsyncSession):
    """POST /api/auth/register/candidate with gdpr_consent=True returns 200."""
    resp = await client.post(
        "/api/auth/register/candidate",
        json={"email": "candidate@example.com", "password": _TEST_PASS, "gdpr_consent": True},
    )
    assert resp.status_code == 200

    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.email == "candidate@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.gdpr_consent is True
    assert user.gdpr_consent_at is not None


@pytest.mark.asyncio
async def test_register_candidate_without_gdpr(client: AsyncClient):
    """POST /api/auth/register/candidate with gdpr_consent=False returns 400."""
    resp = await client.post(
        "/api/auth/register/candidate",
        json={"email": "nogdpr@example.com", "password": _TEST_PASS, "gdpr_consent": False},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_unverified_returns_403(client: AsyncClient):
    """Login without email verification returns 403."""
    await _register(client, "unverified@example.com")
    resp = await client.post(
        "/api/auth/login",
        json={"email": "unverified@example.com", "password": _TEST_PASS},
    )
    assert resp.status_code == 403
    assert "verified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Verified user login returns 200 with access_token and Set-Cookie refresh_token."""
    email = "login_ok@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": _TEST_PASS},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == email

    # Refresh token should be set as a cookie
    assert "refresh_token" in resp.cookies or "set-cookie" in resp.headers


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, db_session: AsyncSession):
    """Login with wrong password returns 401."""
    email = "wrongpass@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassXyz"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Email verification tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient, db_session: AsyncSession):
    """Email verification with valid token sets email_verified=True."""
    email = "verify_me@example.com"
    await _register(client, email)

    token = await _get_verification_token(db_session, email)
    assert token is not None

    resp = await client.post("/api/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert "verified" in resp.json()["message"].lower()

    # Check DB state — reload user
    from sqlalchemy import select

    db_session.expire_all()
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email_verified is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    """Verification with an invalid token returns 400."""
    resp = await client.post("/api/auth/verify-email", json={"token": "bogus-token"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_expired_token(client: AsyncClient, db_session: AsyncSession):
    """Verification with an expired token returns 400."""
    email = "expired_verify@example.com"
    await _register(client, email)

    from sqlalchemy import select

    # Expire the token in DB
    result = await db_session.execute(
        select(EmailToken)
        .join(User, User.id == EmailToken.user_id)
        .where(User.email == email)
    )
    token_record = result.scalar_one_or_none()
    assert token_record is not None
    token_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    resp = await client.post("/api/auth/verify-email", json={"token": token_record.token})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Token refresh tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session: AsyncSession):
    """POST /api/auth/refresh with valid cookie returns new access_token."""
    email = "refresh_me@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": _TEST_PASS},
    )
    assert login_resp.status_code == 200
    # Extract the refresh cookie
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None

    refresh_resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient):
    """POST /api/auth/refresh without cookie returns 401."""
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_invalidates_refresh(client: AsyncClient, db_session: AsyncSession):
    """After logout, the refresh token is revoked and refresh returns 401."""
    email = "logout_me@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    # Login
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": _TEST_PASS},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie is not None

    # Logout
    logout_resp = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies={"refresh_token": refresh_cookie},
    )
    assert logout_resp.status_code == 200

    # Refresh should now fail — token is revoked
    refresh_resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_resp.status_code == 401


# ---------------------------------------------------------------------------
# Forgot password tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email_still_200(client: AsyncClient):
    """POST /api/auth/forgot-password with unknown email returns 200 (no enumeration)."""
    resp = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower() or "if" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_forgot_password_known_email_creates_token(client: AsyncClient, db_session: AsyncSession):
    """POST /api/auth/forgot-password with known email returns 200 and creates reset token."""
    email = "reset_me@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    resp = await client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200

    # Confirm reset token was created in DB
    from sqlalchemy import select

    result = await db_session.execute(
        select(EmailToken)
        .join(User, User.id == EmailToken.user_id)
        .where(User.email == email, EmailToken.token_type == "reset_password")
    )
    token_record = result.scalar_one_or_none()
    assert token_record is not None


# ---------------------------------------------------------------------------
# Password reset tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession):
    """Full password reset flow: register -> verify -> request reset -> apply reset -> login with new pass."""
    email = "full_reset@example.com"
    new_pass = "NewSecurePass99"

    # Register and verify
    await _register(client, email)
    await _set_email_verified(db_session, email)

    # Request reset
    await client.post("/api/auth/forgot-password", json={"email": email})

    # Fetch reset token from DB
    from sqlalchemy import select

    result = await db_session.execute(
        select(EmailToken)
        .join(User, User.id == EmailToken.user_id)
        .where(User.email == email, EmailToken.token_type == "reset_password")
    )
    token_record = result.scalar_one_or_none()
    assert token_record is not None

    # Apply reset
    reset_resp = await client.post(
        "/api/auth/reset-password",
        json={"token": token_record.token, "new_password": new_pass},
    )
    assert reset_resp.status_code == 200

    # Login with new password
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": new_pass},
    )
    assert login_resp.status_code == 200

    # Old password should not work
    old_login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": _TEST_PASS},
    )
    assert old_login_resp.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    """Password reset with bogus token returns 400."""
    resp = await client.post(
        "/api/auth/reset-password",
        json={"token": "bogus-reset-token", "new_password": "NewSecurePass99"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Rate limiting test (skipped in unit test suite)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skip(
    reason=(
        "slowapi in-memory storage rate limiting is per-process and may reset between "
        "test isolation contexts; accurate verification requires a running server."
    )
)
async def test_rate_limit_login(client: AsyncClient, db_session: AsyncSession):
    """Sending 11 rapid login requests should result in 429 on the 11th."""
    email = "ratelimit@example.com"
    await _register(client, email)
    await _set_email_verified(db_session, email)

    responses = []
    for _ in range(11):
        resp = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassXyz"},
        )
        responses.append(resp.status_code)

    assert 429 in responses
