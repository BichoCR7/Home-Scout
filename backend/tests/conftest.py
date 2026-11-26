"""Isolated SQLite fixtures for API and model tests."""

import base64
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    database_path = (tmp_path / "api-test.db").as_posix()
    return Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{database_path}",
        media_storage_dir=tmp_path / "media",
        private_document_storage_dir=tmp_path / "private-documents",
        log_level="WARNING",
        auth_dev_expose_tokens=True,
        finance_encryption_key=base64.urlsafe_b64encode(
            b"12345678901234567890123456789012"
        ).decode(),
        trust_encryption_key=base64.urlsafe_b64encode(b"abcdefghijklmnopqrstuvwxzy123456").decode(),
        message_encryption_key=base64.urlsafe_b64encode(
            b"homescount-message-key-32-bytes!"
        ).decode(),
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    app = create_app(test_settings)
    config = Config("alembic.ini")
    config.attributes["database_url"] = test_settings.database_url
    command.upgrade(config, "head")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
