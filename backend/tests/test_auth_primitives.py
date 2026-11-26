"""Security primitives keep passwords and bearer credentials non-recoverable."""

from uuid import uuid4

import jwt
import pytest

from app.core.auth_tokens import AccessTokenCodec, InvalidAccessToken
from app.services.passwords import PasswordService


def test_password_service_uses_salted_argon2id_hashes() -> None:
    service = PasswordService()
    first = service.hash("a-long-home-scout-password")
    second = service.hash("a-long-home-scout-password")

    assert first.startswith("$argon2id$")
    assert first != second
    assert service.verify(first, "a-long-home-scout-password")
    assert not service.verify(first, "wrong-password")
    assert not service.verify(None, "wrong-password")


def test_access_token_codec_requires_its_fixed_algorithm_and_claims() -> None:
    key = "t" * 64
    codec = AccessTokenCodec(key, lifetime_seconds=600)
    subject_id = uuid4()
    session_id = uuid4()
    encoded, _ = codec.issue(user_id=subject_id, session_id=session_id)
    claims = codec.decode(encoded)

    assert claims["sub"] == str(subject_id)
    assert claims["sid"] == str(session_id)
    assert claims["token_use"] == "access"

    alternative_algorithm = jwt.encode({"sub": str(subject_id)}, key, algorithm="HS512")
    with pytest.raises(InvalidAccessToken):
        codec.decode(alternative_algorithm)
