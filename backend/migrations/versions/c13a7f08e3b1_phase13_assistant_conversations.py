"""Phase 13 HomeScout Assistant conversations, consent, and rate limits.

Revision ID: c13a7f08e3b1
Revises: f12a0a1c9e60
Create Date: 2026-11-24
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "c13a7f08e3b1"
down_revision: str | None = "f12a0a1c9e60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-13:rbac-v1")
_ROLE_PERMISSIONS = {
    role: ("assistant:use:self", "assistant:history:self")
    for role in (
        "tenant",
        "roommate",
        "landlord",
        "real_estate_agent",
        "property_manager",
        "service_provider",
        "moderator",
        "admin",
        "super_admin",
    )
}


def _permission_id(code: str) -> uuid.UUID:
    return uuid.uuid5(_PERMISSION_NAMESPACE, code)


def _seed_permissions() -> None:
    connection = op.get_bind()
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    grants = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
        sa.column("granted_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    role_ids = dict(connection.execute(sa.select(roles.c.code, roles.c.id)).all())
    codes = sorted({code for values in _ROLE_PERMISSIONS.values() for code in values})
    existing = dict(
        connection.execute(
            sa.select(permissions.c.code, permissions.c.id).where(permissions.c.code.in_(codes))
        ).all()
    )
    for code in codes:
        if code not in existing:
            resource, action, scope = code.split(":", maxsplit=2)
            permission_id = _permission_id(code)
            connection.execute(
                permissions.insert().values(
                    id=permission_id,
                    code=code,
                    description=(
                        f"{action.replace('_', ' ').title()} "
                        f"{resource.replace('_', ' ')} in {scope} scope."
                    ),
                    created_at=now,
                )
            )
            existing[code] = permission_id
    for role_code, role_codes in _ROLE_PERMISSIONS.items():
        role_id = role_ids.get(role_code)
        if role_id is None:
            continue
        for code in role_codes:
            permission_id = existing[code]
            present = connection.execute(
                sa.select(grants.c.role_id).where(
                    grants.c.role_id == role_id,
                    grants.c.permission_id == permission_id,
                )
            ).first()
            if present is None:
                connection.execute(
                    grants.insert().values(
                        role_id=role_id,
                        permission_id=permission_id,
                        granted_at=now,
                    )
                )


def _remove_permissions() -> None:
    connection = op.get_bind()
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    grants = sa.table(
        "role_permissions", sa.column("role_id", sa.Uuid()), sa.column("permission_id", sa.Uuid())
    )
    codes = sorted({code for values in _ROLE_PERMISSIONS.values() for code in values})
    role_ids = list(
        connection.scalars(sa.select(roles.c.id).where(roles.c.code.in_(_ROLE_PERMISSIONS)))
    )
    permission_ids = list(
        connection.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes)))
    )
    if role_ids and permission_ids:
        connection.execute(
            grants.delete().where(
                grants.c.role_id.in_(role_ids),
                grants.c.permission_id.in_(permission_ids),
            )
        )
    if permission_ids:
        connection.execute(permissions.delete().where(permissions.c.id.in_(permission_ids)))


def upgrade() -> None:
    op.create_table(
        "assistant_privacy_consents",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_processing_allowed", sa.Boolean(), nullable=False),
        sa.Column("consent_version", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_title", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_conversations_owner_updated",
        "assistant_conversations",
        ["owner_user_id", "updated_at"],
    )
    op.create_table(
        "assistant_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("encrypted_content", sa.LargeBinary(), nullable=False),
        sa.Column("context_property_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name=op.f("ck_assistant_messages_assistant_message_role"),
        ),
        sa.CheckConstraint(
            "sequence_number >= 0", name=op.f("ck_assistant_messages_assistant_message_sequence")
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["assistant_conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "sequence_number", name="uq_assistant_message_conversation_sequence"
        ),
    )
    op.create_index(
        "ix_assistant_messages_conversation_created",
        "assistant_messages",
        ["conversation_id", "created_at"],
    )
    op.create_table(
        "assistant_rate_windows",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    _seed_permissions()


def downgrade() -> None:
    _remove_permissions()
    op.drop_table("assistant_rate_windows")
    op.drop_index("ix_assistant_messages_conversation_created", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_index("ix_assistant_conversations_owner_updated", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
    op.drop_table("assistant_privacy_consents")
