"""Authenticated encryption helpers for messages and private collaboration payloads."""

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


class Phase10Cipher:
    """Encrypt content at rest and bind ciphertext to its owner/resource context."""

    def __init__(self, settings: Settings) -> None:
        encoded = (
            settings.message_encryption_key.get_secret_value()
            if settings.message_encryption_key
            else ""
        )
        if not encoded:
            raise ApiError(
                503,
                "message_encryption_not_configured",
                "Private communication features are unavailable until an encryption key "
                "is configured.",
            )
        key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        self._aes = AESGCM(key)

    def encrypt_message(
        self, conversation_id: UUID, message_id: UUID, sender_id: UUID, body: str
    ) -> bytes:
        aad = b"homescout-message:" + conversation_id.bytes + message_id.bytes + sender_id.bytes
        nonce = os.urandom(12)
        return nonce + self._aes.encrypt(nonce, body.encode("utf-8"), aad)

    def decrypt_message(
        self, conversation_id: UUID, message_id: UUID, sender_id: UUID, ciphertext: bytes
    ) -> str:
        aad = b"homescout-message:" + conversation_id.bytes + message_id.bytes + sender_id.bytes
        try:
            return self._aes.decrypt(ciphertext[:12], ciphertext[12:], aad).decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, ValueError) as error:
            raise ApiError(
                500, "message_unavailable", "This message could not be opened."
            ) from error

    def encrypt_json(
        self, purpose: str, owner_id: UUID, record_id: UUID, payload: dict[str, Any]
    ) -> bytes:
        aad = b"homescout-private:" + purpose.encode("ascii") + owner_id.bytes + record_id.bytes
        nonce = os.urandom(12)
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return nonce + self._aes.encrypt(nonce, encoded, aad)

    def decrypt_json(
        self, purpose: str, owner_id: UUID, record_id: UUID, ciphertext: bytes
    ) -> dict[str, Any]:
        aad = b"homescout-private:" + purpose.encode("ascii") + owner_id.bytes + record_id.bytes
        try:
            decoded = self._aes.decrypt(ciphertext[:12], ciphertext[12:], aad)
            value = json.loads(decoded.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Encrypted private payload must be an object.")
            return value
        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ApiError(
                500, "private_record_unavailable", "This private record could not be opened."
            ) from error

    def encrypt_amount(self, owner_id: UUID, goal_id: UUID, amount: str) -> bytes:
        return self.encrypt_json("shared_goal_amount", owner_id, goal_id, {"amount": amount})

    def decrypt_amount(self, owner_id: UUID, goal_id: UUID, ciphertext: bytes) -> str:
        return self.decrypt_json("shared_goal_amount", owner_id, goal_id, ciphertext).get(
            "amount", ""
        )
