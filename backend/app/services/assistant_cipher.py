"""AES-GCM encryption for user-owned HomeScout Assistant history."""

from __future__ import annotations

import base64
import binascii
import os
import uuid

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings
from app.core.errors import ApiError


class AssistantCipher:
    def __init__(self, settings: Settings) -> None:
        encoded = (
            settings.ai_encryption_key.get_secret_value() if settings.ai_encryption_key else ""
        )
        if not encoded:
            raise ApiError(
                503,
                "assistant_storage_unavailable",
                "Assistant history storage is not configured.",
            )
        try:
            key = base64.urlsafe_b64decode(encoded.encode("ascii") + b"=" * (-len(encoded) % 4))
        except (UnicodeEncodeError, ValueError, binascii.Error) as error:
            raise ApiError(
                503,
                "assistant_storage_unavailable",
                "Assistant history storage is not configured.",
            ) from error
        if len(key) != 32:
            raise ApiError(
                503,
                "assistant_storage_unavailable",
                "Assistant history storage is not configured.",
            )
        self._cipher = AESGCM(key)

    @staticmethod
    def _aad(
        user_id: uuid.UUID, conversation_id: uuid.UUID, item_id: uuid.UUID, purpose: str
    ) -> bytes:
        return f"homescout-assistant:v1:{user_id}:{conversation_id}:{item_id}:{purpose}".encode()

    def encrypt(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        item_id: uuid.UUID,
        purpose: str,
        value: str,
    ) -> bytes:
        nonce = os.urandom(12)
        encrypted = self._cipher.encrypt(
            nonce, value.encode("utf-8"), self._aad(user_id, conversation_id, item_id, purpose)
        )
        return nonce + encrypted

    def decrypt(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        item_id: uuid.UUID,
        purpose: str,
        value: bytes,
    ) -> str:
        try:
            return self._cipher.decrypt(
                value[:12], value[12:], self._aad(user_id, conversation_id, item_id, purpose)
            ).decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, ValueError) as error:
            raise ApiError(
                500,
                "assistant_history_unreadable",
                "This assistant record could not be read.",
            ) from error
