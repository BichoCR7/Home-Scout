"""Registration, verification, password recovery, and revocable sessions."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.core.auth_tokens import AccessTokenCodec, new_secret, secret_digest
from app.core.config import Settings
from app.core.errors import ApiError
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.auth import AccountActionToken, AuthSession, LoginThrottle
from app.models.user import UserAccount, UserProfile
from app.schemas.auth import RegisterRequest
from app.services.authorization import AuthorizationService
from app.services.passwords import password_service

LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_LOCKOUT = timedelta(minutes=15)
MAX_LOGIN_FAILURES = 8


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: UUID
    session_id: UUID


@dataclass(frozen=True, slots=True)
class IssuedAction:
    token: str | None
    recipient: str | None


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class AuthenticationService:
    def __init__(self, settings: Settings, signing_key: str) -> None:
        self.settings = settings
        self.signing_key = signing_key
        self.codec = AccessTokenCodec(
            signing_key, lifetime_seconds=settings.auth_access_ttl_seconds
        )
        self.authorization = AuthorizationService()

    def register(self, session: Session, request: RegisterRequest) -> IssuedAction:
        email = str(request.email).strip().lower()
        user = session.scalar(
            select(UserAccount)
            .options(joinedload(UserAccount.profile))
            .where(func.lower(UserAccount.email) == email)
        )
        if user is None:
            tenant_role = session.scalar(select(Role).where(Role.code == "tenant"))
            if tenant_role is None:
                raise ApiError(
                    status_code=503,
                    code="identity_unavailable",
                    message="Account registration is temporarily unavailable.",
                )
            user = UserAccount(
                email=email,
                password_hash=password_service.hash(request.password.get_secret_value()),
                status="pending",
            )
            user.profile = UserProfile(
                given_name=request.given_name.strip(),
                family_name=request.family_name.strip() if request.family_name else None,
                requested_role_code=request.requested_role_code,
            )
            user.role_assignments.append(
                UserRoleAssignment(
                    role=tenant_role,
                    scope_type="global",
                    scope_id="*",
                )
            )
            session.add(user)
            session.flush()
            self._audit(session, "auth.registration_requested", user.id)
        elif user.status != "pending" or user.email_verified_at is not None:
            session.commit()
            return IssuedAction(token=None, recipient=None)
        elif self._recent_action_exists(session, user.id, "email_verification"):
            session.commit()
            return IssuedAction(token=None, recipient=None)

        token = self._issue_action_token(session, user, purpose="email_verification")
        recipient = user.email
        session.commit()
        return IssuedAction(token=token, recipient=recipient)

    def resend_verification(self, session: Session, email: str) -> IssuedAction:
        normalized_email = email.strip().lower()
        user = session.scalar(
            select(UserAccount).where(func.lower(UserAccount.email) == normalized_email)
        )
        if user is None or user.status != "pending" or user.email_verified_at is not None:
            session.commit()
            return IssuedAction(token=None, recipient=None)
        if self._recent_action_exists(session, user.id, "email_verification"):
            session.commit()
            return IssuedAction(token=None, recipient=None)
        token = self._issue_action_token(session, user, purpose="email_verification")
        session.commit()
        return IssuedAction(token=token, recipient=user.email)

    def verify_email(self, session: Session, token: str) -> None:
        action = self._valid_action_token(session, token, "email_verification")
        if action is None:
            raise self._invalid_action_error()
        now = datetime.now(UTC)
        if not self._consume_action(session, action.id, now):
            raise self._invalid_action_error()
        user = session.get(UserAccount, action.user_id)
        if user is None or user.status != "pending":
            raise self._invalid_action_error()
        user.email_verified_at = now
        user.status = "active"
        self._audit(session, "auth.email_verified", user.id)
        session.commit()

    def request_password_reset(self, session: Session, email: str) -> IssuedAction:
        normalized_email = email.strip().lower()
        user = session.scalar(
            select(UserAccount).where(func.lower(UserAccount.email) == normalized_email)
        )
        if (
            user is None
            or user.status != "active"
            or user.email_verified_at is None
            or self._recent_action_exists(session, user.id, "password_reset")
        ):
            session.commit()
            return IssuedAction(token=None, recipient=None)
        token = self._issue_action_token(session, user, purpose="password_reset")
        session.commit()
        return IssuedAction(token=token, recipient=user.email)

    def confirm_password_reset(self, session: Session, *, token: str, new_password: str) -> None:
        action = self._valid_action_token(session, token, "password_reset")
        if action is None:
            raise self._invalid_action_error()
        now = datetime.now(UTC)
        if not self._consume_action(session, action.id, now):
            raise self._invalid_action_error()
        user = session.get(UserAccount, action.user_id)
        if user is None or user.status != "active":
            raise self._invalid_action_error()
        user.password_hash = password_service.hash(new_password)
        session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        self._audit(session, "auth.password_reset", user.id)
        session.commit()

    def login(self, session: Session, *, email: str, password: str) -> TokenPair:
        normalized_email = email.strip().lower()
        throttle_key = self._throttle_key(normalized_email)
        now = datetime.now(UTC)
        throttle = session.get(LoginThrottle, throttle_key)
        if throttle and throttle.locked_until and _utc(throttle.locked_until) > now:
            raise ApiError(
                status_code=429,
                code="login_temporarily_limited",
                message="Sign-in is temporarily unavailable. Try again later.",
            )

        user = session.scalar(
            select(UserAccount)
            .options(joinedload(UserAccount.profile))
            .where(func.lower(UserAccount.email) == normalized_email)
        )
        correct_password = password_service.verify(
            user.password_hash if user else None,
            password,
        )
        if user is None or not correct_password:
            self._record_failed_login(session, throttle, throttle_key, now)
            raise ApiError(
                status_code=401,
                code="invalid_credentials",
                message="Email or password is incorrect.",
            )

        if user.status != "active" or user.email_verified_at is None:
            self._clear_login_throttle(session, throttle)
            session.commit()
            raise ApiError(
                status_code=403,
                code="email_verification_required",
                message="Verify your email address before signing in.",
            )

        if user.password_hash and password_service.needs_rehash(user.password_hash):
            user.password_hash = password_service.hash(password)
        self._clear_login_throttle(session, throttle)
        pair = self._create_session(session, user.id)
        self._audit(session, "auth.login", user.id)
        session.commit()
        return pair

    def refresh(self, session: Session, refresh_token: str) -> TokenPair:
        token_hash = secret_digest(refresh_token)
        auth_session = session.scalar(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        now = datetime.now(UTC)
        if (
            auth_session is None
            or auth_session.revoked_at is not None
            or _utc(auth_session.expires_at) <= now
        ):
            raise self._invalid_session_error()
        user = session.get(UserAccount, auth_session.user_id)
        if user is None or user.status != "active" or user.email_verified_at is None:
            auth_session.revoked_at = now
            session.commit()
            raise self._invalid_session_error()

        replacement = new_secret()
        changed = session.execute(
            update(AuthSession)
            .where(
                AuthSession.id == auth_session.id,
                AuthSession.refresh_token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .values(refresh_token_hash=secret_digest(replacement), last_used_at=now)
            .execution_options(synchronize_session=False)
        ).rowcount
        if changed != 1:
            session.rollback()
            raise self._invalid_session_error()
        access_token, _ = self.codec.issue(user_id=user.id, session_id=auth_session.id)
        session.commit()
        return TokenPair(
            access_token=access_token,
            refresh_token=replacement,
            expires_in=self.settings.auth_access_ttl_seconds,
        )

    def authenticate(self, session: Session, access_token: str) -> AuthenticatedPrincipal:
        try:
            claims = self.codec.decode(access_token)
            user_id = UUID(str(claims["sub"]))
            session_id = UUID(str(claims["sid"]))
        except (ValueError, KeyError, TypeError) as exc:
            raise self._invalid_session_error() from exc
        auth_session = session.get(AuthSession, session_id)
        now = datetime.now(UTC)
        if (
            auth_session is None
            or auth_session.user_id != user_id
            or auth_session.revoked_at is not None
            or _utc(auth_session.expires_at) <= now
        ):
            raise self._invalid_session_error()
        user = session.get(UserAccount, user_id)
        if user is None or user.status != "active" or user.email_verified_at is None:
            raise self._invalid_session_error()
        return AuthenticatedPrincipal(user_id=user_id, session_id=session_id)

    def logout(self, session: Session, refresh_token: str) -> None:
        auth_session = session.scalar(
            select(AuthSession).where(
                AuthSession.refresh_token_hash == secret_digest(refresh_token)
            )
        )
        if auth_session and auth_session.revoked_at is None:
            now = datetime.now(UTC)
            auth_session.revoked_at = now
            self._audit(session, "auth.logout", auth_session.user_id)
            session.commit()

    def list_sessions(self, session: Session, user_id: UUID) -> list[AuthSession]:
        now = datetime.now(UTC)
        return list(
            session.scalars(
                select(AuthSession)
                .where(
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > now,
                )
                .order_by(AuthSession.created_at.desc())
            )
        )

    def revoke_session(self, session: Session, *, user_id: UUID, session_id: UUID) -> None:
        auth_session = session.scalar(
            select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        if auth_session is None:
            raise ApiError(status_code=404, code="session_not_found", message="Session not found.")
        auth_session.revoked_at = datetime.now(UTC)
        self._audit(session, "auth.session_revoked", user_id)
        session.commit()

    def update_profile(
        self,
        session: Session,
        *,
        user_id: UUID,
        given_name: str | None,
        family_name: str | None,
        preferred_name: str | None,
    ) -> UserAccount:
        user = session.scalar(
            select(UserAccount)
            .options(joinedload(UserAccount.profile))
            .where(UserAccount.id == user_id)
        )
        if user is None or user.profile is None:
            raise ApiError(status_code=404, code="user_not_found", message="User not found.")
        if given_name is not None:
            user.profile.given_name = given_name.strip()
        if family_name is not None:
            user.profile.family_name = family_name.strip() or None
        if preferred_name is not None:
            user.profile.preferred_name = preferred_name.strip() or None
        session.commit()
        return user

    def _create_session(self, session: Session, user_id: UUID) -> TokenPair:
        refresh = new_secret()
        now = datetime.now(UTC)
        auth_session = AuthSession(
            user_id=user_id,
            refresh_token_hash=secret_digest(refresh),
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=self.settings.auth_refresh_ttl_days),
        )
        session.add(auth_session)
        session.flush()
        access, _ = self.codec.issue(user_id=user_id, session_id=auth_session.id)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.settings.auth_access_ttl_seconds,
        )

    def _issue_action_token(
        self,
        session: Session,
        user: UserAccount,
        *,
        purpose: str,
    ) -> str:
        now = datetime.now(UTC)
        session.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.user_id == user.id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        token = new_secret()
        session.add(
            AccountActionToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=secret_digest(token),
                created_at=now,
                expires_at=now + timedelta(minutes=self.settings.auth_action_ttl_minutes),
            )
        )
        return token

    def _valid_action_token(
        self,
        session: Session,
        token: str,
        purpose: str,
    ) -> AccountActionToken | None:
        action = session.scalar(
            select(AccountActionToken).where(
                AccountActionToken.token_hash == secret_digest(token),
                AccountActionToken.purpose == purpose,
                AccountActionToken.consumed_at.is_(None),
            )
        )
        if action is None or _utc(action.expires_at) <= datetime.now(UTC):
            return None
        return action

    @staticmethod
    def _consume_action(session: Session, action_id: UUID, now: datetime) -> bool:
        changed = session.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.id == action_id,
                AccountActionToken.consumed_at.is_(None),
                AccountActionToken.expires_at > now,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        ).rowcount
        return changed == 1

    def _recent_action_exists(self, session: Session, user_id: UUID, purpose: str) -> bool:
        threshold = datetime.now(UTC) - timedelta(seconds=60)
        action = session.scalar(
            select(AccountActionToken.id)
            .where(
                AccountActionToken.user_id == user_id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.created_at > threshold,
            )
            .limit(1)
        )
        return action is not None

    def _record_failed_login(
        self,
        session: Session,
        throttle: LoginThrottle | None,
        identity_hash: str,
        now: datetime,
    ) -> None:
        if throttle is None:
            throttle = LoginThrottle(
                identity_hash=identity_hash,
                failure_count=0,
                window_started_at=now,
            )
            session.add(throttle)
        elif now - _utc(throttle.window_started_at) > LOGIN_WINDOW:
            throttle.failure_count = 0
            throttle.window_started_at = now
            throttle.locked_until = None
        throttle.failure_count += 1
        if throttle.failure_count >= MAX_LOGIN_FAILURES:
            throttle.locked_until = now + LOGIN_LOCKOUT
        session.commit()

    @staticmethod
    def _clear_login_throttle(session: Session, throttle: LoginThrottle | None) -> None:
        if throttle is not None:
            session.delete(throttle)

    def _throttle_key(self, email: str) -> str:
        return hmac.new(
            self.signing_key.encode("utf-8"),
            f"login:{email}".encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _audit(session: Session, event_type: str, user_id: UUID) -> None:
        session.add(AuditEvent(event_type=event_type, actor_user_id=user_id))

    @staticmethod
    def _invalid_action_error() -> ApiError:
        return ApiError(
            status_code=400,
            code="invalid_or_expired_action_token",
            message="This code is invalid or has expired.",
        )

    @staticmethod
    def _invalid_session_error() -> ApiError:
        return ApiError(
            status_code=401,
            code="authentication_required",
            message="Sign in again to continue.",
        )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
