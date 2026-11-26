"""Consent-aware HomeScout Assistant orchestration and private history."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.data_access.assistant import AssistantDataAccess
from app.models.assistant import (
    AssistantConversation,
    AssistantMessage,
    AssistantPrivacyConsent,
    AssistantRateWindow,
)
from app.models.user import UserAccount
from app.schemas.assistant import (
    AssistantConfigurationResponse,
    AssistantConversationDetailResponse,
    AssistantConversationResponse,
    AssistantMessageRequest,
    AssistantMessageResponse,
    AssistantMessageResult,
    AssistantPrivacyResponse,
    AssistantPrivacyUpdate,
    AssistantRenameRequest,
)
from app.services.ai_provider import AiProviderUnavailable
from app.services.assistant_cipher import AssistantCipher
from app.services.assistant_context import AssistantContextBuilder
from app.services.authorization import AuthorizationService

logger = logging.getLogger("homescout.ai")
PRIVACY_POLICY_VERSION = "assistant-2026-11-24-v1"
PRIVACY_NOTICE = (
    "When enabled, your message and the bounded conversation history are sent to the configured "
    "AI provider to produce a reply. Account context is sent only when you select it for that "
    "message. HomeScout encrypts saved conversations at rest. You can withdraw provider consent "
    "and delete conversations at any time. Do not send passwords, payment credentials, or another "
    "person's private information. AI replies can be wrong and are not legal, credit, lending, or "
    "financial decisions."
)


class AssistantService:
    def __init__(self, settings: Settings, provider: object) -> None:
        self.settings = settings
        self.provider = provider
        self.data = AssistantDataAccess()
        self.authorization = AuthorizationService()

    def configuration(self) -> AssistantConfigurationResponse:
        available = self._available()
        return AssistantConfigurationResponse(
            available=available,
            provider_label="Configured AI provider" if available else "Not connected",
            consent_version=self._consent_version(),
            privacy_notice=PRIVACY_NOTICE,
            disabled_message=None
            if available
            else ("HomeScout Assistant is not connected yet. No generated replies are available."),
        )

    def require_access(self, session: Session, user_id: UUID, code: str) -> None:
        self._require_permission(session, user_id, code)

    def privacy(self, session: Session, user_id: UUID) -> AssistantPrivacyResponse:
        row = self.data.consent(session, user_id)
        version = self._consent_version()
        return AssistantPrivacyResponse(
            provider_processing_allowed=bool(
                row and row.provider_processing_allowed and row.consent_version == version
            ),
            consent_version=version,
            updated_at=row.updated_at if row else None,
            ai_available=self._available(),
            at_rest_encryption_configured=bool(self.settings.ai_encryption_key),
        )

    def update_privacy(
        self, session: Session, user_id: UUID, body: AssistantPrivacyUpdate
    ) -> AssistantPrivacyResponse:
        if body.provider_processing_allowed and not self._available():
            raise ApiError(
                409,
                "assistant_unavailable",
                "HomeScout Assistant is not connected to an AI provider yet.",
            )
        row = self.data.consent(session, user_id)
        if row is None:
            row = AssistantPrivacyConsent(
                user_id=user_id,
                provider_processing_allowed=body.provider_processing_allowed,
                consent_version=self._consent_version(),
            )
            session.add(row)
        else:
            row.provider_processing_allowed = body.provider_processing_allowed
            row.consent_version = self._consent_version()
        session.commit()
        session.refresh(row)
        return self.privacy(session, user_id)

    def list_conversations(
        self, session: Session, user_id: UUID, limit: int = 50
    ) -> list[AssistantConversationResponse]:
        self._require_permission(session, user_id, "assistant:history:self")
        cipher = AssistantCipher(self.settings)
        rows = self.data.conversations(session, user_id, min(max(limit, 1), 100))
        return [self._conversation_response(cipher, row) for row in rows]

    def get_conversation(
        self, session: Session, user_id: UUID, conversation_id: UUID
    ) -> AssistantConversationDetailResponse:
        row = self._owned_conversation(session, user_id, conversation_id)
        cipher = AssistantCipher(self.settings)
        messages = self.data.messages(session, row.id)
        return AssistantConversationDetailResponse(
            **self._conversation_response(cipher, row).model_dump(),
            messages=[self._message_response(cipher, user_id, row.id, item) for item in messages],
        )

    def rename(
        self, session: Session, user_id: UUID, conversation_id: UUID, body: AssistantRenameRequest
    ) -> AssistantConversationResponse:
        row = self._owned_conversation(session, user_id, conversation_id)
        cipher = AssistantCipher(self.settings)
        row.encrypted_title = cipher.encrypt(user_id, row.id, row.id, "title", body.title)
        row.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(row)
        return self._conversation_response(cipher, row)

    def delete(self, session: Session, user_id: UUID, conversation_id: UUID) -> None:
        session.delete(self._owned_conversation(session, user_id, conversation_id))
        session.commit()

    def send(
        self, session: Session, user_id: UUID, request: AssistantMessageRequest
    ) -> AssistantMessageResult:
        self._require_permission(session, user_id, "assistant:use:self")
        if not self._available():
            raise ApiError(
                503,
                "assistant_unavailable",
                "HomeScout Assistant is not connected to an AI provider yet.",
            )
        consent = self.data.consent(session, user_id)
        if (
            not consent
            or not consent.provider_processing_allowed
            or consent.consent_version != self._consent_version()
        ):
            raise ApiError(
                403,
                "assistant_consent_required",
                "Review and accept the AI data-processing notice before sending a message.",
            )
        self._consume_rate_limit(session, user_id)

        existing = None
        history: list[dict[str, str]] = []
        cipher = AssistantCipher(self.settings)
        if request.conversation_id:
            existing = self._owned_conversation(session, user_id, request.conversation_id)
            recent = self.data.messages(
                session, existing.id, limit=self.settings.ai_history_messages
            )
            history = [
                {
                    "role": item.role,
                    "content": cipher.decrypt(
                        user_id, existing.id, item.id, "message", item.encrypted_content
                    ),
                }
                for item in recent
            ]
        context = AssistantContextBuilder(self.settings).build(
            session, user_id=user_id, request=request
        )
        instructions = self._instructions(
            request.intent, self.authorization.role_codes(session, user_id), context.text
        )
        provider_messages = [*history, {"role": "user", "content": request.text}]
        session.commit()
        try:
            answer = self.provider.complete(instructions, provider_messages)
        except AiProviderUnavailable:
            logger.warning("assistant_provider_unavailable")
            raise ApiError(
                503,
                "assistant_provider_unavailable",
                (
                    "The AI provider did not return a reply. Your message was not saved; "
                    "please try again later."
                ),
            ) from None

        conversation = existing
        if conversation is None:
            conversation = AssistantConversation(
                id=uuid4(), owner_user_id=user_id, encrypted_title=b"pending"
            )
            session.add(conversation)
            session.flush()
        else:
            # Serialize appends to an existing thread after provider latency.
            conversation = session.scalar(
                select(AssistantConversation)
                .where(
                    AssistantConversation.id == conversation.id,
                    AssistantConversation.owner_user_id == user_id,
                )
                .with_for_update()
            )
            if conversation is None:
                raise ApiError(
                    404,
                    "assistant_conversation_not_found",
                    "That conversation was not found.",
                )
        if conversation.encrypted_title == b"pending":
            title = request.text[:72].strip() or "HomeScout conversation"
            conversation.encrypted_title = cipher.encrypt(
                user_id, conversation.id, conversation.id, "title", title
            )
        user_message = self._store_message(
            session, cipher, user_id, conversation.id, "user", request.text, context.property_ids
        )
        assistant_message = self._store_message(
            session, cipher, user_id, conversation.id, "assistant", answer, context.property_ids
        )
        conversation.updated_at = datetime.now(UTC)
        session.commit()
        session.refresh(conversation)
        session.refresh(user_message)
        session.refresh(assistant_message)
        return AssistantMessageResult(
            conversation=self._conversation_response(cipher, conversation),
            user_message=self._message_response(cipher, user_id, conversation.id, user_message),
            assistant_message=self._message_response(
                cipher, user_id, conversation.id, assistant_message
            ),
            context_properties=context.properties,
        )

    def _consume_rate_limit(self, session: Session, user_id: UUID) -> None:
        account = session.scalar(
            select(UserAccount).where(UserAccount.id == user_id).with_for_update()
        )
        if account is None:
            raise ApiError(401, "authentication_required", "Sign in to continue.")
        now = datetime.now(UTC)
        window = session.scalar(
            select(AssistantRateWindow)
            .where(AssistantRateWindow.user_id == user_id)
            .with_for_update()
        )
        if window is None:
            window = AssistantRateWindow(user_id=user_id, window_started_at=now, request_count=0)
            session.add(window)
            session.flush()
        window_started = window.window_started_at
        if window_started.tzinfo is None:
            window_started = window_started.replace(tzinfo=UTC)
        if window_started < now - timedelta(minutes=1):
            window.window_started_at, window.request_count = now, 0
        if window.request_count >= self.settings.ai_requests_per_minute:
            session.rollback()
            raise ApiError(
                429,
                "assistant_rate_limited",
                "You have sent several assistant requests. Wait a minute and try again.",
            )
        window.request_count += 1
        session.commit()

    def _require_permission(self, session: Session, user_id: UUID, code: str) -> None:
        self.authorization.require_permission(
            session, user_id=user_id, permission_code=code, resource_owner_id=user_id
        )

    def _owned_conversation(
        self, session: Session, user_id: UUID, conversation_id: UUID
    ) -> AssistantConversation:
        self._require_permission(session, user_id, "assistant:history:self")
        row = self.data.conversation(session, user_id, conversation_id)
        if row is None:
            raise ApiError(
                404, "assistant_conversation_not_found", "That conversation was not found."
            )
        return row

    def _conversation_response(
        self, cipher: AssistantCipher, row: AssistantConversation
    ) -> AssistantConversationResponse:
        return AssistantConversationResponse(
            id=row.id,
            title=cipher.decrypt(row.owner_user_id, row.id, row.id, "title", row.encrypted_title),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _message_response(cipher, user_id, conversation_id, row) -> AssistantMessageResponse:
        return AssistantMessageResponse(
            id=row.id,
            role=row.role,
            text=cipher.decrypt(user_id, conversation_id, row.id, "message", row.encrypted_content),
            context_property_ids=row.context_property_ids,
            created_at=row.created_at,
        )

    @staticmethod
    def _store_message(session, cipher, user_id, conversation_id, role, content, property_ids):
        last_sequence = session.scalar(
            select(AssistantMessage.sequence_number)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.sequence_number.desc())
            .limit(1)
        )
        item_id = uuid4()
        row = AssistantMessage(
            id=item_id,
            conversation_id=conversation_id,
            sequence_number=last_sequence + 1 if last_sequence is not None else 0,
            role=role,
            encrypted_content=cipher.encrypt(user_id, conversation_id, item_id, "message", content),
            context_property_ids=property_ids,
        )
        session.add(row)
        session.flush()
        return row

    def _available(self) -> bool:
        return bool(
            self.settings.ai_enabled
            and self.settings.ai_api_base_url
            and self.settings.ai_model
            and self.settings.ai_api_key
            and self.settings.ai_encryption_key
        )

    def _consent_version(self) -> str:
        destination = "|".join(
            (
                PRIVACY_POLICY_VERSION,
                self.settings.ai_provider,
                self.settings.ai_api_protocol,
                (self.settings.ai_api_base_url or "").lower(),
                self.settings.ai_model or "",
            )
        )
        digest = hashlib.sha256(destination.encode()).hexdigest()[:12]
        return f"{PRIVACY_POLICY_VERSION}.{digest}"

    @staticmethod
    def _instructions(intent: str, roles: list[str], context: str) -> str:
        return "\n".join(
            (
                "You are HomeScout Assistant, a housing and rental-planning helper for Kenya.",
                f"The user's selected intent is: {intent}.",
                "The signed-in account's roles are: "
                f"{', '.join(roles) if roles else 'none recorded'}.",
                "",
                "Use KSh/KES for Kenyan costs. Never invent properties, prices,",
                "availability, verification, reviews, bookings, service or payment status,",
                "neighbourhood statistics, legal facts, or financial records.",
                "Treat supplied records as the only HomeScout facts.",
                "Search results are snapshots, not guarantees.",
                "State when information is unavailable.",
                "Do not expose another person's private data.",
                "RentScore/readiness is a user-input planning index, not a credit score",
                "or eligibility decision. Explain supplied costs and label assumptions.",
                "Do not promise outcomes or provide investment/lending decisions.",
                "Explain lease wording plainly, not as legal advice.",
                "Acknowledge that AI can be mistaken.",
                "Do not claim to complete app actions.",
                "",
                "Authorized data explicitly selected for this message:",
                context,
            )
        )
