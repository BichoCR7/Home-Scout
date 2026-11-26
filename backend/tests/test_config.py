"""Environment configuration validation tests."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_settings_load_environment_values(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    database_path = (tmp_path / "env.db").as_posix()
    monkeypatch.setenv("HOMESCOUT_ENVIRONMENT", "test")
    monkeypatch.setenv("HOMESCOUT_DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("HOMESCOUT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HOMESCOUT_CORS_ORIGINS", '["https://android.example"]')

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.database_url == f"sqlite:///{database_path}"
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins == ["https://android.example"]


def test_rejects_unsupported_database_schemes() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="mysql+pymysql://host/db")


def test_production_requires_postgresql_and_disables_docs() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", database_url="sqlite:///./local.db")

    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://user:placeholder@db.example/homescout",
        auth_signing_key=SecretStr("a" * 48),
        finance_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        trust_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        message_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        smtp_host="smtp.example",
        smtp_from="accounts@example.test",
    )
    assert settings.docs_enabled is False


def test_staging_requires_server_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="staging")


def test_cors_rejects_paths_and_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["https://example.com/api"])
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=["https://user:secret@example.com"])


def test_ai_configuration_is_server_only_and_requires_https_and_encryption() -> None:
    defaults = Settings(_env_file=None)
    assert defaults.ai_enabled is False

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="test",
            ai_enabled=True,
            ai_api_base_url="https://provider.example/v1",
            ai_model="test-model",
            ai_api_key=SecretStr("server-secret"),
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://user:placeholder@db.example/homescout",
            ai_api_base_url="http://provider.example/v1",
        )
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="test",
            ai_enabled=True,
            ai_api_base_url="https://provider.example/v1",
            ai_model="test-model",
            ai_api_key=SecretStr("server-secret"),
            ai_encryption_key=SecretStr("not-a-valid-key"),
        )

    settings = Settings(
        _env_file=None,
        environment="test",
        ai_enabled=True,
        ai_api_base_url="https://provider.example/v1",
        ai_model="test-model",
        ai_api_key=SecretStr("server-secret"),
        ai_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
    )
    assert settings.ai_enabled is True
    assert settings.ai_api_protocol == "responses"


def test_mpesa_is_disabled_by_default_and_requires_complete_sandbox_configuration() -> None:
    disabled = Settings(_env_file=None)
    assert disabled.mpesa_enabled is False
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mpesa_enabled=True)

    configured = Settings(
        _env_file=None,
        environment="test",
        mpesa_enabled=True,
        mpesa_environment="sandbox",
        mpesa_consumer_key=SecretStr("sandbox-key"),
        mpesa_consumer_secret=SecretStr("sandbox-secret"),
        mpesa_business_shortcode="174379",
        mpesa_passkey=SecretStr("sandbox-passkey"),
        mpesa_callback_base_url="https://callbacks.example.com/homescout",
        mpesa_phone_hash_key=SecretStr("payment-hmac-key-with-at-least-32-bytes"),
    )
    assert configured.mpesa_enabled is True
    assert configured.mpesa_environment == "sandbox"
    assert configured.mpesa_transaction_type == "CustomerPayBillOnline"


def test_mpesa_rejects_non_https_callbacks_invalid_shortcode_and_short_privacy_key() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mpesa_callback_base_url="http://callbacks.example.com")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mpesa_business_shortcode="short")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="test",
            mpesa_enabled=True,
            mpesa_environment="sandbox",
            mpesa_consumer_key=SecretStr("key"),
            mpesa_consumer_secret=SecretStr("secret"),
            mpesa_business_shortcode="174379",
            mpesa_passkey=SecretStr("passkey"),
            mpesa_callback_base_url="https://callbacks.example.com",
            mpesa_phone_hash_key=SecretStr("too-short"),
        )
