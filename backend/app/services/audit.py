"""Audit-event service; commits remain owned by the calling transaction."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditService:
    def record(
        self,
        session: Session,
        *,
        event_type: str,
        actor_user_id: UUID | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Stage a sanitized audit event; caller commits or rolls it back."""

        event = AuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            subject_type=subject_type,
            subject_id=subject_id,
            request_id=request_id,
            metadata_json=metadata,
        )
        session.add(event)
        return event
