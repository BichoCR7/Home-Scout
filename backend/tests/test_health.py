"""Health and baseline HTTP response tests."""

import re

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


def test_liveness_endpoint_and_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "phase2.check-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "phase2.check-1"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "not a safe id"})

    assert response.status_code == 200
    assert re.fullmatch(r"[a-f0-9]{32}", response.headers["X-Request-ID"])


def test_readiness_uses_database_connection(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_safe_error_when_database_cannot_open(tmp_path) -> None:
    missing_directory = (tmp_path / "missing" / "database.db").as_posix()
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{missing_directory}",
        log_level="CRITICAL",
    )
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert "database.db" not in response.text


def test_unknown_route_uses_consistent_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]
    assert "/not-a-route" not in response.text


def test_production_hides_interactive_api_docs() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+psycopg://user:placeholder@db.example/homescout",
        auth_signing_key=SecretStr("a" * 48),
        finance_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        trust_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        message_encryption_key=SecretStr("MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="),
        smtp_host="smtp.example.com",
        smtp_from="accounts@example.com",
    )
    app: FastAPI = create_app(settings)
    try:
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    finally:
        app.state.db_engine.dispose()
