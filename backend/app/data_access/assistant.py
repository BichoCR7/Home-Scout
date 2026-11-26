"""Owner-scoped data access for HomeScout Assistant history and consent."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assistant import AssistantConversation, AssistantMessage, AssistantPrivacyConsent


class AssistantDataAccess:
    def consent(self, session: Session, user_id: UUID) -> AssistantPrivacyConsent | None:
        return session.get(AssistantPrivacyConsent, user_id)

    def conversation(
        self, session: Session, user_id: UUID, conversation_id: UUID
    ) -> AssistantConversation | None:
        return session.scalar(
            select(AssistantConversation).where(
                AssistantConversation.id == conversation_id,
                AssistantConversation.owner_user_id == user_id,
            )
        )

    def conversations(
        self, session: Session, user_id: UUID, limit: int
    ) -> list[AssistantConversation]:
        return list(
            session.scalars(
                select(AssistantConversation)
                .where(AssistantConversation.owner_user_id == user_id)
                .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id)
                .limit(limit)
            )
        )

    def messages(
        self,
        session: Session,
        conversation_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[AssistantMessage]:
        statement = (
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == conversation_id)
            .order_by(AssistantMessage.sequence_number.desc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = list(session.scalars(statement))
        rows.reverse()
        return rows
