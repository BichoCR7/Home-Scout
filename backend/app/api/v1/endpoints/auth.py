"""Public identity operations and authenticated self-service account endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_auth_service, get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.models.user import UserAccount
from app.schemas.auth import (
    AccountActionRequest,
    AuthMessageResponse,
    AuthUserResponse,
    EmailRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
    TokenPairResponse,
    UserProfileResponse,
)
from app.services.authentication import (
    AuthenticatedPrincipal,
    AuthenticationService,
    IssuedAction,
)
from app.services.authorization import AuthorizationService
from app.services.identity_email import IdentityEmailDelivery

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthMessageResponse, status_code=status.HTTP_202_ACCEPTED)
def register(
    body: RegisterRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthMessageResponse:
    issued = service.register(session, body)
    _send_verification(settings, issued)
    return AuthMessageResponse(
        message="If the address can be registered, verification instructions have been sent.",
        development_token=_development_token(settings, issued),
    )


@router.post("/email/verify", response_model=AuthMessageResponse)
def verify_email(
    body: AccountActionRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> AuthMessageResponse:
    service.verify_email(session, body.token)
    return AuthMessageResponse(message="Email verified. You can now sign in.")


@router.post(
    "/email/resend",
    response_model=AuthMessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resend_verification(
    body: EmailRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthMessageResponse:
    issued = service.resend_verification(session, str(body.email))
    _send_verification(settings, issued)
    return AuthMessageResponse(
        message="If the address needs verification, a code has been sent.",
        development_token=_development_token(settings, issued),
    )


@router.post("/login", response_model=TokenPairResponse)
def login(
    body: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> TokenPairResponse:
    pair = service.login(
        session,
        email=str(body.email),
        password=body.password.get_secret_value(),
    )
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(
    body: RefreshRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> TokenPairResponse:
    pair = service.refresh(session, body.refresh_token)
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    body: LogoutRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> Response:
    service.logout(session, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password-reset/request", response_model=AuthMessageResponse, status_code=202)
def request_password_reset(
    body: EmailRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthMessageResponse:
    issued = service.request_password_reset(session, str(body.email))
    if issued.recipient and issued.token:
        IdentityEmailDelivery(settings).send_password_reset(issued.recipient, issued.token)
    return AuthMessageResponse(
        message="If an eligible account uses that address, reset instructions have been sent.",
        development_token=_development_token(settings, issued),
    )


@router.post("/password-reset/confirm", response_model=AuthMessageResponse)
def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> AuthMessageResponse:
    service.confirm_password_reset(
        session,
        token=body.token,
        new_password=body.new_password.get_secret_value(),
    )
    return AuthMessageResponse(message="Password changed. Sign in with your new password.")


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> AuthUserResponse:
    AuthorizationService().require_permission(
        session,
        user_id=principal.user_id,
        permission_code="profile:view:self",
        resource_owner_id=principal.user_id,
    )
    user = _load_user(session, principal.user_id)
    return _user_response(session, user)


@router.patch("/me", response_model=AuthUserResponse)
def update_me(
    body: ProfileUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> AuthUserResponse:
    AuthorizationService().require_permission(
        session,
        user_id=principal.user_id,
        permission_code="profile:edit:self",
        resource_owner_id=principal.user_id,
    )
    user = service.update_profile(
        session,
        user_id=principal.user_id,
        given_name=body.given_name,
        family_name=body.family_name,
        preferred_name=body.preferred_name,
    )
    return _user_response(session, user)


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> list[SessionResponse]:
    AuthorizationService().require_permission(
        session,
        user_id=principal.user_id,
        permission_code="session:view:self",
        resource_owner_id=principal.user_id,
    )
    sessions = service.list_sessions(session, principal.user_id)
    return [
        SessionResponse(
            id=item.id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            current=item.id == principal.session_id,
        )
        for item in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(
    session_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> Response:
    AuthorizationService().require_permission(
        session,
        user_id=principal.user_id,
        permission_code="session:revoke:self",
        resource_owner_id=principal.user_id,
    )
    service.revoke_session(session, user_id=principal.user_id, session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _send_verification(settings: Settings, issued: IssuedAction) -> None:
    if issued.recipient and issued.token:
        IdentityEmailDelivery(settings).send_verification(issued.recipient, issued.token)


def _development_token(settings: Settings, issued: IssuedAction) -> str | None:
    if settings.auth_dev_expose_tokens and issued.recipient:
        return issued.token
    return None


def _load_user(session: Session, user_id: UUID) -> UserAccount:
    user = session.scalar(
        select(UserAccount)
        .options(joinedload(UserAccount.profile))
        .where(UserAccount.id == user_id)
    )
    if user is None:
        raise ApiError(status_code=404, code="user_not_found", message="User not found.")
    return user


def _user_response(session: Session, user: UserAccount) -> AuthUserResponse:
    authorization = AuthorizationService()
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        profile=(
            UserProfileResponse(
                given_name=user.profile.given_name,
                family_name=user.profile.family_name,
                preferred_name=user.profile.preferred_name,
                requested_role_code=user.profile.requested_role_code,
            )
            if user.profile
            else None
        ),
        roles=authorization.role_codes(session, user.id),
        permissions=authorization.permission_codes(session, user.id),
    )
