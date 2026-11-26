"""FastAPI dependency providers."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.services.authentication import AuthenticatedPrincipal, AuthenticationService

bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield one request-scoped database session and always close it."""

    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_auth_service(request: Request) -> AuthenticationService:
    """Provide the process-scoped signing key and validated settings."""

    return AuthenticationService(
        request.app.state.settings,
        request.app.state.auth_signing_key,
    )


def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    session: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(
            status_code=401,
            code="authentication_required",
            message="Sign in to continue.",
        )
    return service.authenticate(session, credentials.credentials)


def get_optional_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    session: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal | None:
    if credentials is None:
        return None
    return service.authenticate(session, credentials.credentials)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
