"""Plain-text verification and password-reset delivery over configured SMTP."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger("homescout.identity_email")


class IdentityEmailDelivery:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_verification(self, email: str, token: str) -> bool:
        return self._send(
            email,
            subject="Verify your HomeScout account",
            body=(
                "Use this one-time code to verify your HomeScout email address:\n\n"
                f"{token}\n\nIt expires shortly. If you did not create this account, "
                "ignore this message."
            ),
        )

    def send_password_reset(self, email: str, token: str) -> bool:
        return self._send(
            email,
            subject="Reset your HomeScout password",
            body=(
                "Use this one-time code to reset your HomeScout password:\n\n"
                f"{token}\n\nIt expires shortly. If you did not request a reset, "
                "ignore this message."
            ),
        )

    def _send(self, recipient: str, *, subject: str, body: str) -> bool:
        if not self._settings.smtp_host or not self._settings.smtp_from:
            return False

        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(
                self._settings.smtp_host, self._settings.smtp_port, timeout=10
            ) as client:
                client.ehlo()
                if self._settings.smtp_starttls:
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if self._settings.smtp_username:
                    password = (
                        self._settings.smtp_password.get_secret_value()
                        if self._settings.smtp_password
                        else None
                    )
                    client.login(self._settings.smtp_username, password or "")
                client.send_message(message)
            return True
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("identity_email_delivery_failed error_type=%s", type(exc).__name__)
            return False
