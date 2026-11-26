"""Authorized, encrypted account messaging scoped to an existing relationship."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.audit import AuditEvent
from app.models.marketplace import PropertyEnquiry
from app.models.notification import InAppNotification
from app.models.personal_hub import PrivateDocument
from app.models.phase10 import (
    CollaborationGroup,
    CollaborationGroupMember,
    Conversation,
    ConversationBlock,
    ConversationMessage,
    ConversationParticipant,
    MessageAttachment,
    MessageReport,
    RoommateInterest,
)
from app.models.property import Property
from app.models.user import UserAccount
from app.schemas.phase10 import (
    ConversationResponse,
    MessageAttachmentResponse,
    MessageCreate,
    MessageReportCreate,
    MessageResponse,
)
from app.services.authorization import AuthorizationService
from app.services.phase10_cipher import Phase10Cipher

ALLOWED_ATTACHMENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


class CommunicationsService:
    def __init__(self, cipher: Phase10Cipher) -> None:
        self.cipher = cipher
        self.authorization = AuthorizationService()

    def inbox(
        self, session: Session, user_id: UUID, *, include_archived: bool = False
    ) -> list[ConversationResponse]:
        participant = ConversationParticipant
        statement = (
            select(Conversation, participant)
            .join(participant, participant.conversation_id == Conversation.id)
            .where(participant.user_id == user_id, participant.is_active.is_(True))
        )
        if not include_archived:
            statement = statement.where(participant.archived_at.is_(None))
        rows = session.execute(
            statement.order_by(Conversation.last_message_at.desc().nullslast())
        ).all()
        return [self._conversation_response(session, row, user_id) for row in rows]

    def get_or_create_for_enquiry(
        self, session: Session, user_id: UUID, enquiry_id: UUID
    ) -> ConversationResponse:
        enquiry = session.get(PropertyEnquiry, enquiry_id)
        if enquiry is None or user_id not in {enquiry.sender_user_id, enquiry.recipient_user_id}:
            raise self.not_found("The enquiry was not found.")
        if enquiry.status == "closed":
            raise ApiError(409, "enquiry_closed", "A closed enquiry cannot start a conversation.")
        conversation = session.scalar(
            select(Conversation).where(Conversation.property_enquiry_id == enquiry.id)
        )
        if conversation is None:
            conversation = Conversation(property_enquiry_id=enquiry.id, created_by_user_id=user_id)
            session.add(conversation)
            session.flush()
            session.add_all(
                [
                    ConversationParticipant(
                        conversation_id=conversation.id, user_id=enquiry.sender_user_id
                    ),
                    ConversationParticipant(
                        conversation_id=conversation.id, user_id=enquiry.recipient_user_id
                    ),
                ]
            )
            session.flush()
        participant = self._require_participant(session, conversation.id, user_id)
        self._require_conversation_permission(session, user_id, conversation.id)
        participant.archived_at = None
        session.commit()
        return self._conversation_response(session, (conversation, participant), user_id)

    def get_or_create_for_roommate_interest(
        self, session: Session, user_id: UUID, interest_id: UUID
    ) -> ConversationResponse:
        interest = session.get(RoommateInterest, interest_id)
        if (
            interest is None
            or interest.status != "accepted"
            or user_id not in {interest.requester_user_id, interest.target_user_id}
        ):
            raise self.not_found("The accepted roommate connection was not found.")
        conversation = session.scalar(
            select(Conversation).where(Conversation.roommate_interest_id == interest.id)
        )
        if conversation is None:
            conversation = Conversation(
                roommate_interest_id=interest.id, created_by_user_id=user_id
            )
            session.add(conversation)
            session.flush()
            session.add_all(
                [
                    ConversationParticipant(
                        conversation_id=conversation.id, user_id=interest.requester_user_id
                    ),
                    ConversationParticipant(
                        conversation_id=conversation.id, user_id=interest.target_user_id
                    ),
                ]
            )
            session.flush()
        participant = self._require_participant(session, conversation.id, user_id)
        self._require_conversation_permission(session, user_id, conversation.id)
        participant.archived_at = None
        session.commit()
        return self._conversation_response(session, (conversation, participant), user_id)

    def group_conversation(
        self, session: Session, user_id: UUID, group_id: UUID
    ) -> ConversationResponse:
        conversation = session.scalar(select(Conversation).where(Conversation.group_id == group_id))
        if conversation is None:
            raise self.not_found("The group conversation was not found.")
        participant = self._require_participant(session, conversation.id, user_id)
        self._require_conversation_permission(session, user_id, conversation.id)
        participant.archived_at = None
        session.commit()
        return self._conversation_response(session, (conversation, participant), user_id)

    def messages(
        self, session: Session, user_id: UUID, conversation_id: UUID, *, limit: int
    ) -> list[MessageResponse]:
        conversation = self._require_conversation(session, conversation_id, user_id)
        self._require_conversation_permission(session, user_id, conversation.id)
        participant = self._require_participant(session, conversation.id, user_id)
        rows = list(
            session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation.id)
                .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
                .limit(limit)
            )
        )
        participant.last_read_at = datetime.now(UTC)
        session.commit()
        return [self._message_response(session, row) for row in reversed(rows)]

    def send_message(
        self,
        session: Session,
        user_id: UUID,
        conversation_id: UUID,
        body: MessageCreate,
        *,
        request_id: str | None = None,
    ) -> MessageResponse:
        conversation = self._require_conversation(session, conversation_id, user_id)
        self._require_conversation_permission(session, user_id, conversation.id)
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="conversation:send:participant",
            resource_scope_type="conversation",
            resource_scope_id=str(conversation.id),
        )
        self._require_not_blocked(session, conversation, user_id)
        now = datetime.now(UTC)
        recent = (
            session.scalar(
                select(func.count())
                .select_from(ConversationMessage)
                .where(
                    ConversationMessage.sender_user_id == user_id,
                    ConversationMessage.created_at >= now - timedelta(minutes=5),
                )
            )
            or 0
        )
        if recent >= 30:
            raise ApiError(429, "message_rate_limited", "Please wait before sending more messages.")
        documents = self._validate_attachments(session, user_id, body.attachment_document_ids)
        row = ConversationMessage(
            id=uuid4(),
            conversation_id=conversation.id,
            sender_user_id=user_id,
            encrypted_body=b"",
            created_at=now,
        )
        row.encrypted_body = self.cipher.encrypt_message(
            conversation.id, row.id, user_id, body.body
        )
        session.add(row)
        session.flush()
        for document in documents:
            session.add(
                MessageAttachment(
                    message_id=row.id,
                    document_id=document.id,
                    attached_by_user_id=user_id,
                )
            )
        conversation.last_message_at = now
        recipient_ids = list(
            session.scalars(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id == conversation.id,
                    ConversationParticipant.is_active.is_(True),
                    ConversationParticipant.user_id != user_id,
                )
            )
        )
        for recipient_id in recipient_ids:
            session.add(
                InAppNotification(
                    recipient_user_id=recipient_id,
                    category="message",
                    title="New HomeScout message",
                    body="You have a new message in HomeScout.",
                    target_path=f"/collaboration?conversationId={conversation.id}&tab=Messages",
                )
            )
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="conversation.message_sent",
                subject_type="conversation",
                subject_id=str(conversation.id),
                request_id=request_id,
                metadata_json={"message_id": str(row.id), "attachment_count": len(documents)},
            )
        )
        session.commit()
        return self._message_response(session, row)

    def archive(self, session: Session, user_id: UUID, conversation_id: UUID) -> None:
        participant = self._require_participant(session, conversation_id, user_id)
        participant.archived_at = datetime.now(UTC)
        session.commit()

    def set_block(
        self, session: Session, user_id: UUID, other_user_id: UUID, *, blocked: bool
    ) -> None:
        if user_id == other_user_id or session.get(UserAccount, other_user_id) is None:
            raise self.not_found("The account was not found.")
        row = session.get(ConversationBlock, (user_id, other_user_id))
        if blocked and row is None:
            session.add(ConversationBlock(blocker_user_id=user_id, blocked_user_id=other_user_id))
        elif not blocked and row is not None:
            session.delete(row)
        session.commit()

    def blocks(self, session: Session, user_id: UUID) -> list[dict[str, object]]:
        return [
            {"blocked_user_id": row.blocked_user_id, "created_at": row.created_at}
            for row in session.scalars(
                select(ConversationBlock)
                .where(ConversationBlock.blocker_user_id == user_id)
                .order_by(ConversationBlock.created_at.desc())
            )
        ]

    def report_message(
        self,
        session: Session,
        user_id: UUID,
        message_id: UUID,
        body: MessageReportCreate,
        *,
        request_id: str | None = None,
    ) -> UUID:
        message = session.get(ConversationMessage, message_id)
        if message is None:
            raise self.not_found("The message was not found.")
        self._require_participant(session, message.conversation_id, user_id)
        self._require_conversation_permission(session, user_id, message.conversation_id)
        if message.sender_user_id == user_id:
            raise ApiError(409, "cannot_report_own_message", "You cannot report your own message.")
        existing = session.scalar(
            select(MessageReport.id).where(
                MessageReport.message_id == message.id,
                MessageReport.reporter_user_id == user_id,
            )
        )
        if existing:
            raise ApiError(409, "message_already_reported", "You already reported this message.")
        row = MessageReport(
            message_id=message.id,
            reporter_user_id=user_id,
            category=body.category,
            details=body.details,
        )
        session.add(row)
        session.add(
            AuditEvent(
                actor_user_id=user_id,
                event_type="conversation.message_reported",
                subject_type="conversation_message",
                subject_id=str(message.id),
                request_id=request_id,
                metadata_json={"category": body.category},
            )
        )
        session.commit()
        return row.id

    def attachment_file(
        self,
        session: Session,
        user_id: UUID,
        message_id: UUID,
        document_id: UUID,
    ) -> PrivateDocument:
        message = session.get(ConversationMessage, message_id)
        if message is None:
            raise self.not_found("The message attachment was not found.")
        self._require_participant(session, message.conversation_id, user_id)
        self._require_conversation_permission(session, user_id, message.conversation_id)
        linked = session.scalar(
            select(MessageAttachment.id).where(
                MessageAttachment.message_id == message.id,
                MessageAttachment.document_id == document_id,
            )
        )
        document = session.get(PrivateDocument, document_id)
        if linked is None or document is None or document.category == "verification":
            raise self.not_found("The message attachment was not found.")
        return document

    def _validate_attachments(
        self, session: Session, owner_id: UUID, document_ids: list[UUID]
    ) -> list[PrivateDocument]:
        if not document_ids:
            return []
        documents = list(
            session.scalars(select(PrivateDocument).where(PrivateDocument.id.in_(document_ids)))
        )
        if len(documents) != len(document_ids) or any(
            document.owner_user_id != owner_id
            or document.category == "verification"
            or document.storage_encrypted
            or document.content_type not in ALLOWED_ATTACHMENT_TYPES
            or document.size_bytes > 15_728_640
            for document in documents
        ):
            raise ApiError(
                422,
                "invalid_message_attachment",
                "Attach an allowed PDF or image from your private documents.",
            )
        return documents

    def _conversation_response(
        self, session: Session, row: tuple[Conversation, ConversationParticipant], user_id: UUID
    ) -> ConversationResponse:
        conversation, participant = row
        if conversation.property_enquiry_id:
            enquiry = session.get(PropertyEnquiry, conversation.property_enquiry_id)
            property_ = session.get(Property, enquiry.property_id) if enquiry else None
            title = property_.title if property_ else "Property enquiry"
            context = "property_enquiry"
            property_id = property_.id if property_ else None
        elif conversation.group_id:
            group = session.get(CollaborationGroup, conversation.group_id)
            title = group.name if group else "Shared group"
            context = "shared_group"
            property_id = None
        else:
            title = "Roommate connection"
            context = "roommate"
            property_id = None
        unread = 0
        count_query = (
            select(func.count())
            .select_from(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.sender_user_id != user_id,
            )
        )
        if participant.last_read_at is not None:
            count_query = count_query.where(
                ConversationMessage.created_at > participant.last_read_at
            )
        unread = session.scalar(count_query) or 0
        return ConversationResponse(
            id=conversation.id,
            context=context,
            property_id=property_id,
            group_id=conversation.group_id,
            title=title,
            last_message_at=conversation.last_message_at,
            unread_count=unread,
            archived=participant.archived_at is not None,
        )

    def _message_response(self, session: Session, row: ConversationMessage) -> MessageResponse:
        body = self.cipher.decrypt_message(
            row.conversation_id, row.id, row.sender_user_id, row.encrypted_body
        )
        attachments = []
        for attachment in session.scalars(
            select(MessageAttachment).where(MessageAttachment.message_id == row.id)
        ):
            document = session.get(PrivateDocument, attachment.document_id)
            if document is not None:
                attachments.append(
                    MessageAttachmentResponse(
                        document_id=document.id,
                        filename=document.original_filename,
                        content_type=document.content_type,
                    )
                )
        return MessageResponse(
            id=row.id,
            sender_user_id=row.sender_user_id,
            body=body,
            attachments=attachments,
            created_at=row.created_at,
        )

    def _require_conversation(
        self, session: Session, conversation_id: UUID, user_id: UUID
    ) -> Conversation:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None or conversation.closed_at is not None:
            raise self.not_found("The conversation was not found.")
        self._require_participant(session, conversation.id, user_id)
        return conversation

    @staticmethod
    def _require_participant(
        session: Session, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant:
        participant = session.get(ConversationParticipant, (conversation_id, user_id))
        if participant is None or not participant.is_active:
            raise ApiError(404, "conversation_not_found", "The conversation was not found.")
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None and conversation.group_id is not None:
            membership = session.get(CollaborationGroupMember, (conversation.group_id, user_id))
            if membership is None or membership.status != "active":
                raise ApiError(404, "conversation_not_found", "The conversation was not found.")
        return participant

    def _require_conversation_permission(
        self, session: Session, user_id: UUID, conversation_id: UUID
    ) -> None:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="conversation:view:participant",
            resource_scope_type="conversation",
            resource_scope_id=str(conversation_id),
        )

    def _require_not_blocked(
        self, session: Session, conversation: Conversation, sender_id: UUID
    ) -> None:
        if conversation.group_id is not None:
            return
        blocked_ids = set(
            session.scalars(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id == conversation.id,
                    ConversationParticipant.user_id != sender_id,
                )
            )
        )
        if not blocked_ids:
            return
        recipient_id = next(iter(blocked_ids))
        blocked = session.scalar(
            select(ConversationBlock.blocker_user_id).where(
                or_(
                    (ConversationBlock.blocker_user_id == sender_id)
                    & (ConversationBlock.blocked_user_id == recipient_id),
                    (ConversationBlock.blocker_user_id == recipient_id)
                    & (ConversationBlock.blocked_user_id == sender_id),
                )
            )
        )
        if blocked is not None:
            raise ApiError(403, "conversation_blocked", "This conversation is unavailable.")

    @staticmethod
    def not_found(message: str) -> ApiError:
        return ApiError(404, "conversation_not_found", message)
