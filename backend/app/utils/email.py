"""Async email sending utility using aiosmtplib.

Mailpit is used for development (no auth, no TLS).
Production SMTP is configured via environment variables.
"""
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.utils.logging import logger


async def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP (async)."""
    msg = MIMEText(html_body, "html")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject

    smtp_kwargs: dict = {
        "hostname": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
    }

    # Only add credentials if SMTP_USER is configured (mailpit needs no auth)
    if settings.SMTP_USER:
        smtp_kwargs["username"] = settings.SMTP_USER
        smtp_kwargs["password"] = settings.SMTP_PASSWORD

    if settings.SMTP_USE_TLS:
        smtp_kwargs["start_tls"] = True

    try:
        await aiosmtplib.send(msg, **smtp_kwargs)
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as exc:
        # Log but do not raise — email failure should not break auth flow in most cases.
        # The caller decides whether to propagate.
        logger.error(f"Failed to send email to {to}: {exc}")
        raise


async def send_verification_email(to: str, token: str) -> None:
    """Send an email-verification link to the user."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html_body = f"""
    <html>
      <body>
        <h2>Verify your Bryton AI account</h2>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_url}">{verify_url}</a></p>
        <p>This link expires in 24 hours.</p>
        <p>If you did not create this account, you can safely ignore this email.</p>
      </body>
    </html>
    """
    await send_email(to, "Verify your Bryton AI account", html_body)


async def send_password_reset_email(to: str, token: str) -> None:
    """Send a password-reset link to the user."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html_body = f"""
    <html>
      <body>
        <h2>Reset your Bryton AI password</h2>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_url}">{reset_url}</a></p>
        <p>This link expires in 1 hour.</p>
        <p>If you did not request a password reset, you can safely ignore this email.</p>
      </body>
    </html>
    """
    await send_email(to, "Reset your Bryton AI password", html_body)
