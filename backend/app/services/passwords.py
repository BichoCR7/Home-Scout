"""Argon2id password hashing and verification."""

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class PasswordService:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=2,
            memory_cost=19_456,
            parallelism=1,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash("HomeScout-invalid-login-timing-value")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, stored_hash: str | None, password: str) -> bool:
        candidate = stored_hash or self._dummy_hash
        try:
            return (
                self._hasher.verify(candidate, password)
                if stored_hash
                else self._dummy_verify(password)
            )
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False

    def needs_rehash(self, stored_hash: str) -> bool:
        return self._hasher.check_needs_rehash(stored_hash)

    def _dummy_verify(self, password: str) -> bool:
        try:
            self._hasher.verify(self._dummy_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            pass
        return False


password_service = PasswordService()
