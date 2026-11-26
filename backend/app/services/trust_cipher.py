"""Authenticated encryption for viewing details and user-submitted trust reports."""

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


class TrustCipher:
    """Encrypt sensitive user-supplied trust data, bound to its account owner."""

    def __init__(self, settings: Settings) -> None:
        encoded = (
            settings.trust_encryption_key.get_secret_value()
            if settings.trust_encryption_key
            else ""
        )
        if not encoded:
            raise ApiError(
                503,
                "trust_encryption_not_configured",
                (
                    "Private trust and safety features are unavailable until an encryption "
                    "key is configured."
                ),
            )
        key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        self._aes = AESGCM(key)

    def encrypt(self, owner_id: UUID, payload: dict[str, Any]) -> bytes:
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        return nonce + self._aes.encrypt(nonce, plaintext, owner_id.bytes)

    def encrypt_document(self, owner_id: UUID, document_id: UUID, contents: bytes) -> bytes:
        nonce = os.urandom(12)
        associated_data = b"verification-document:" + owner_id.bytes + document_id.bytes
        return nonce + self._aes.encrypt(nonce, contents, associated_data)

    def decrypt_document(self, owner_id: UUID, document_id: UUID, ciphertext: bytes) -> bytes:
        try:
            associated_data = b"verification-document:" + owner_id.bytes + document_id.bytes
            return self._aes.decrypt(ciphertext[:12], ciphertext[12:], associated_data)
        except (InvalidTag, ValueError) as error:
            raise ApiError(
                500,
                "trust_document_unavailable",
                "This private verification document could not be opened.",
            ) from error

    def decrypt(self, owner_id: UUID, ciphertext: bytes) -> dict[str, Any]:
        try:
            plaintext = self._aes.decrypt(ciphertext[:12], ciphertext[12:], owner_id.bytes)
            value = json.loads(plaintext.decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Trust data must be an object.")
            return value
        except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ApiError(
                500,
                "trust_data_unavailable",
                "This private trust and safety record could not be opened.",
            ) from error
