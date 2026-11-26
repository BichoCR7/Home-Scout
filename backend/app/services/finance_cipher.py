"""Authenticated encryption for private SmartRent payloads."""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings
from app.core.errors import ApiError


class FinanceCipher:
    """AES-GCM payload encryption bound to the owning account as associated data."""

    def __init__(self, settings: Settings) -> None:
        encoded = (
            settings.finance_encryption_key.get_secret_value()
            if settings.finance_encryption_key
            else ""
        )
        if not encoded:
            raise ApiError(
                503,
                "finance_encryption_not_configured",
                "Private finance features are unavailable until an encryption key is configured.",
            )
        key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        self._aes = AESGCM(key)

    def encrypt(self, owner_id: UUID, payload: dict[str, Any]) -> bytes:
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return nonce + self._aes.encrypt(nonce, plaintext, owner_id.bytes)

    def decrypt(self, owner_id: UUID, ciphertext: bytes) -> dict[str, Any]:
        try:
            plaintext = self._aes.decrypt(ciphertext[:12], ciphertext[12:], owner_id.bytes)
            value = json.loads(plaintext.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Finance payload must be an object.")
            return value
        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ApiError(
                500,
                "finance_data_unavailable",
                "This private finance record could not be opened.",
            ) from error
