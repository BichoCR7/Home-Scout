"""Phase 14 platform operations and support workflow fields.

Revision ID: d14a9c2e5f81
Revises: c13a7f08e3b1
Create Date: 2026-11-24
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "d14a9c2e5f81"
down_revision: str | None = "c13a7f08e3b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-14:rbac-v1")
_ROLE_CODES = ("admin", "super_admin")


def _seed_service_permission() -> None:
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
    code = "service:manage:platform"
    permission_id = uuid.uuid5(_NAMESPACE, code)
    now = datetime.now(UTC)
    if connection.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).first():
        permission_id = connection.execute(
            sa.select(permissions.c.id).where(permissions.c.code == code)
        ).scalar_one()
    else:
        connection.execute(
            permissions.insert().values(
                id=permission_id,
                code=code,
                description=(
                    "Manage published provider profiles and service offerings platform-wide."
                ),
                created_at=now,
            )
        )
    role_ids = dict(
        connection.execute(
            sa.select(roles.c.code, roles.c.id).where(roles.c.code.in_(_ROLE_CODES))
        ).all()
    )
    for role_code in _ROLE_CODES:
        role_id = role_ids.get(role_code)
        if role_id is None:
            continue
        exists = connection.execute(
            sa.select(grants.c.role_id).where(
                grants.c.role_id == role_id, grants.c.permission_id == permission_id
            )
        ).first()
        if exists is None:
            connection.execute(
                grants.insert().values(role_id=role_id, permission_id=permission_id, granted_at=now)
            )


def _remove_service_permission() -> None:
    connection = op.get_bind()
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    grants = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    permission_ids = sa.select(permissions.c.id).where(
        permissions.c.code == "service:manage:platform"
    )
    role_ids = sa.select(roles.c.id).where(roles.c.code.in_(_ROLE_CODES))
    connection.execute(
        grants.delete().where(
            grants.c.permission_id.in_(permission_ids), grants.c.role_id.in_(role_ids)
        )
    )
    connection.execute(permissions.delete().where(permissions.c.id.in_(permission_ids)))


def upgrade() -> None:
    with op.batch_alter_table("service_reviews") as batch_op:
        batch_op.add_column(
            sa.Column(
                "moderation_status", sa.String(length=24), nullable=False, server_default="clear"
            )
        )
        batch_op.create_check_constraint(
            "service_review_moderation_status",
            "moderation_status IN ('clear','under_review','removed')",
        )

    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.add_column(
            sa.Column("priority", sa.String(length=12), nullable=False, server_default="normal")
        )
        batch_op.add_column(sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_support_tickets_assigned_to_user_id_user_accounts",
            "user_accounts",
            ["assigned_to_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "support_ticket_priority", "priority IN ('normal', 'high', 'urgent')"
        )

    op.create_table(
        "support_ticket_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_ticket_actions_ticket_created",
        "support_ticket_actions",
        ["ticket_id", "created_at"],
    )
    _seed_service_permission()


def downgrade() -> None:
    _remove_service_permission()
    op.drop_index("ix_support_ticket_actions_ticket_created", table_name="support_ticket_actions")
    op.drop_table("support_ticket_actions")
    with op.batch_alter_table("support_tickets") as batch_op:
        batch_op.drop_constraint("support_ticket_priority", type_="check")
        batch_op.drop_constraint(
            "fk_support_tickets_assigned_to_user_id_user_accounts", type_="foreignkey"
        )
        batch_op.drop_column("escalated_at")
        batch_op.drop_column("assigned_to_user_id")
        batch_op.drop_column("priority")
    with op.batch_alter_table("service_reviews") as batch_op:
        batch_op.drop_constraint("service_review_moderation_status", type_="check")
        batch_op.drop_column("moderation_status")
