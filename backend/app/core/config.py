"""Validated environment-based application configuration."""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings; secrets are not returned through application APIs."""

    model_config = SettingsConfigDict(
        env_prefix="HOMESCOUT_",
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "HomeScout API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    database_url: str = Field(default="sqlite:///./homescout.db", repr=False)
    media_storage_dir: Path = Field(default=BACKEND_ROOT / "var" / "property-media", repr=False)
    media_max_image_bytes: int = Field(default=10_485_760, ge=1024, le=52_428_800)
    map_geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    private_document_storage_dir: Path = Field(
        default=BACKEND_ROOT / "var" / "private-documents", repr=False
    )
    private_document_max_bytes: int = Field(default=15_728_640, ge=1024, le=52_428_800)
    finance_encryption_key: SecretStr | None = Field(default=None, repr=False)
    trust_encryption_key: SecretStr | None = Field(default=None, repr=False)
    message_encryption_key: SecretStr | None = Field(default=None, repr=False)
    ai_enabled: bool = False
    ai_provider: Literal["openai_compatible"] = "openai_compatible"
    ai_api_protocol: Literal["responses", "chat_completions"] = "responses"
    ai_api_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: SecretStr | None = Field(default=None, repr=False)
    ai_encryption_key: SecretStr | None = Field(default=None, repr=False)
    ai_request_timeout_seconds: int = Field(default=30, ge=5, le=90)
    ai_requests_per_minute: int = Field(default=10, ge=1, le=60)
    ai_history_messages: int = Field(default=16, ge=2, le=40)
    mpesa_enabled: bool = False
    mpesa_environment: Literal["sandbox", "production"] = "sandbox"
    mpesa_transaction_type: Literal["CustomerPayBillOnline", "CustomerBuyGoodsOnline"] = (
        "CustomerPayBillOnline"
    )
    mpesa_consumer_key: SecretStr | None = Field(default=None, repr=False)
    mpesa_consumer_secret: SecretStr | None = Field(default=None, repr=False)
    mpesa_business_shortcode: str | None = None
    mpesa_passkey: SecretStr | None = Field(default=None, repr=False)
    mpesa_callback_base_url: str | None = None
    mpesa_phone_hash_key: SecretStr | None = Field(default=None, repr=False)
    mpesa_service_collection_authorized: bool = False
    mpesa_request_timeout_seconds: int = Field(default=15, ge=3, le=60)
    mpesa_reconciliation_cooldown_seconds: int = Field(default=30, ge=5, le=3600)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: list[str] = Field(default_factory=list)
    auth_signing_key: SecretStr | None = Field(default=None, repr=False)
    auth_access_ttl_seconds: int = Field(default=600, ge=300, le=1800)
    auth_refresh_ttl_days: int = Field(default=30, ge=1, le=90)
    auth_action_ttl_minutes: int = Field(default=30, ge=5, le=120)
    auth_dev_expose_tokens: bool = False
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = Field(default=None, repr=False)
    smtp_from: str | None = None
    smtp_starttls: bool = True

    @field_validator("auth_signing_key")
    @classmethod
    def signing_key_length(cls, value: SecretStr | None) -> SecretStr | None:
        if (
            value is not None
            and value.get_secret_value()
            and len(value.get_secret_value().encode("utf-8")) < 32
        ):
            raise ValueError("Authentication signing keys must contain at least 32 bytes.")
        return value

    @field_validator("database_url")
    @classmethod
    def supported_database_url(cls, value: str) -> str:
        scheme = urlsplit(value).scheme.lower()
        if scheme not in {"sqlite", "postgresql", "postgresql+psycopg"}:
            raise ValueError("Database URL must use SQLite or PostgreSQL with psycopg.")
        if not value.strip():
            raise ValueError("Database URL must not be empty.")
        return value

    @field_validator("map_geocoder_url")
    @classmethod
    def validate_map_geocoder_url(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Map geocoder URL must be an HTTPS endpoint without credentials or query data."
            )
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized: list[str] = []
        for origin in origins:
            candidate = origin.strip().rstrip("/")
            parsed = urlsplit(candidate)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS origins must be complete HTTP or HTTPS origins.")
            if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise ValueError("CORS entries must be origins without paths or credentials.")
            normalized.append(candidate)
        return normalized

    @field_validator("finance_encryption_key")
    @classmethod
    def validate_finance_encryption_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        try:
            encoded = value.get_secret_value().encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError("Finance encryption key must be URL-safe base64.") from error
        try:
            decoded = base64.urlsafe_b64decode(encoded + b"=" * (-len(encoded) % 4))
        except (ValueError, binascii.Error) as error:
            raise ValueError(
                "Finance encryption key must be a URL-safe base64 32-byte key."
            ) from error
        if len(decoded) != 32:
            raise ValueError("Finance encryption key must decode to exactly 32 bytes.")
        return value

    @field_validator("trust_encryption_key")
    @classmethod
    def validate_trust_encryption_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        try:
            encoded = value.get_secret_value().encode("ascii")
            decoded = base64.urlsafe_b64decode(encoded + b"=" * (-len(encoded) % 4))
        except (UnicodeEncodeError, ValueError, binascii.Error) as error:
            raise ValueError(
                "Trust encryption key must be a URL-safe base64 32-byte key."
            ) from error
        if len(decoded) != 32:
            raise ValueError("Trust encryption key must decode to exactly 32 bytes.")
        return value

    @field_validator("message_encryption_key")
    @classmethod
    def validate_message_encryption_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        try:
            encoded = value.get_secret_value().encode("ascii")
            decoded = base64.urlsafe_b64decode(encoded + b"=" * (-len(encoded) % 4))
        except (UnicodeEncodeError, ValueError, binascii.Error) as error:
            raise ValueError(
                "Message encryption key must be a URL-safe base64 32-byte key."
            ) from error
        if len(decoded) != 32:
            raise ValueError("Message encryption key must decode to exactly 32 bytes.")
        return value

    @field_validator("ai_encryption_key")
    @classmethod
    def validate_ai_encryption_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None or not value.get_secret_value():
            return None
        try:
            encoded = value.get_secret_value().encode("ascii")
            decoded = base64.urlsafe_b64decode(encoded + b"=" * (-len(encoded) % 4))
        except (UnicodeEncodeError, ValueError, binascii.Error) as error:
            raise ValueError("AI encryption key must be URL-safe base64.") from error
        if len(decoded) != 32:
            raise ValueError("AI encryption key must decode to exactly 32 bytes.")
        return value

    @field_validator("ai_api_base_url")
    @classmethod
    def validate_ai_api_base_url(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "AI API base URL must be an HTTPS URL without credentials or query data."
            )
        local_host = parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
        environment = info.data.get("environment", "development")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and local_host and environment in {"development", "test"}
        ):
            raise ValueError("AI API base URL must use HTTPS outside a local development endpoint.")
        return normalized

    @field_validator(
        "mpesa_consumer_key",
        "mpesa_consumer_secret",
        "mpesa_passkey",
        "mpesa_phone_hash_key",
        mode="before",
    )
    @classmethod
    def empty_mpesa_secrets_are_missing(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator("mpesa_business_shortcode")
    @classmethod
    def validate_mpesa_shortcode(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if not normalized.isdigit() or not 5 <= len(normalized) <= 12:
            raise ValueError("M-Pesa business shortcode must contain 5 to 12 digits.")
        return normalized

    @field_validator("mpesa_callback_base_url")
    @classmethod
    def validate_mpesa_callback_base_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Daraja callback base URL must be an HTTPS origin or path.")
        hostname = parsed.hostname.lower()
        if hostname in {"localhost", "127.0.0.1", "::1"} or "." not in hostname:
            raise ValueError("Daraja callbacks require a public HTTPS host.")
        return normalized

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> Settings:
        if self.environment == "production" and urlsplit(self.database_url).scheme.lower() not in {
            "postgresql",
            "postgresql+psycopg",
        }:
            raise ValueError("Production requires a PostgreSQL database URL.")
        if self.auth_dev_expose_tokens and self.environment not in {"development", "test"}:
            raise ValueError("Development token output is available only in development and tests.")
        if self.environment in {"staging", "production"}:
            if not self.finance_encryption_key:
                raise ValueError("Staging and production require a finance encryption key.")
            if not self.trust_encryption_key:
                raise ValueError("Staging and production require a trust encryption key.")
            if not self.message_encryption_key:
                raise ValueError("Staging and production require a message encryption key.")
            signing_key = self.auth_signing_key.get_secret_value() if self.auth_signing_key else ""
            if len(signing_key.encode("utf-8")) < 32:
                raise ValueError(
                    "Staging and production require an authentication signing key "
                    "of 32 bytes or more."
                )
            if not self.smtp_host or not self.smtp_from:
                raise ValueError(
                    "Staging and production require SMTP_HOST and SMTP_FROM "
                    "for account recovery mail."
                )
            if not self.smtp_starttls:
                raise ValueError("Staging and production require SMTP STARTTLS.")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together.")
        mpesa_secrets = (
            self.mpesa_consumer_key,
            self.mpesa_consumer_secret,
            self.mpesa_passkey,
            self.mpesa_phone_hash_key,
        )
        if self.mpesa_enabled:
            if not self.mpesa_business_shortcode or not self.mpesa_callback_base_url:
                raise ValueError(
                    "Enabled M-Pesa payments require a shortcode and public HTTPS callback URL."
                )
            if any(secret is None or not secret.get_secret_value() for secret in mpesa_secrets):
                raise ValueError("Enabled M-Pesa payments require all Daraja credentials and keys.")
            phone_key = self.mpesa_phone_hash_key.get_secret_value()
            if len(phone_key.encode("utf-8")) < 32:
                raise ValueError("The payment privacy key must contain at least 32 bytes.")
            if self.mpesa_environment == "production":
                if self.environment != "production":
                    raise ValueError("Daraja production mode is allowed only in production.")
                if not self.mpesa_service_collection_authorized:
                    raise ValueError(
                        "Production service-payment collection requires explicit authorization."
                    )
            elif self.environment == "production":
                raise ValueError("Production applications must not send payments to the sandbox.")
        if self.ai_enabled:
            if not self.ai_api_base_url or not self.ai_model:
                raise ValueError("Enabled AI requires a provider base URL and model name.")
            if self.ai_api_key is None or not self.ai_api_key.get_secret_value():
                raise ValueError("Enabled AI requires a provider API key.")
            if self.ai_encryption_key is None:
                raise ValueError("Enabled AI requires an at-rest conversation encryption key.")
            if (
                self.environment in {"staging", "production"}
                and urlsplit(self.ai_api_base_url).scheme != "https"
            ):
                raise ValueError("Staging and production AI providers require HTTPS.")
        if self.mpesa_service_collection_authorized and not self.mpesa_enabled:
            raise ValueError(
                "Service-payment collection cannot be authorized while payments are disabled."
            )
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.environment not in {"staging", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for the running process."""

    return Settings()
