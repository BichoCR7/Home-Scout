"""add authentication sessions and scoped RBAC

Revision ID: bdb6297372fc
Revises: b5d5b46e253a
Create Date: 2026-11-23 10:30:13.511347
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "bdb6297372fc"
down_revision: str | None = "b5d5b46e253a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-3:rbac-seed-v1")
_ROLES = (
    ("tenant", "Tenant / House Hunter", "Renter and housing search account."),
    ("roommate", "Roommate / Shared Search Member", "Member of explicitly shared groups."),
    ("landlord", "Landlord / Property Owner", "Owner access for owned property workflows."),
    ("real_estate_agent", "Real Estate Agent", "Access to assigned listing work."),
    ("property_manager", "Property Manager", "Access to assigned portfolio workflows."),
    ("service_provider", "Service Provider", "Access to own services and assigned bookings."),
    ("moderator", "Moderator", "Access to reported content and moderation workflows."),
    ("admin", "Admin", "Limited operational administration."),
    ("super_admin", "Super Admin", "Audited platform security and role administration."),
)
_ROLE_PERMISSIONS = {
    "tenant": (
        "account:edit:self",
        "account:view:self",
        "activity:view:self",
        "booking:view:self",
        "conversation:view:participant",
        "document:view:self",
        "financial_record:view:self",
        "listing:view:public",
        "profile:edit:self",
        "profile:view:self",
        "property:view:public",
        "session:revoke:self",
        "session:view:self",
        "shared_group:view:member",
    ),
    "roommate": (
        "account:view:self",
        "profile:view:self",
        "session:revoke:self",
        "session:view:self",
        "shared_collection:view:member",
        "shared_comparison:view:member",
        "shared_financial_goal:view:shared",
        "shared_group:view:member",
        "shared_task:view:member",
        "shared_viewing:view:member",
    ),
    "landlord": (
        "account:view:self",
        "conversation:view:participant",
        "enquiry:view:assigned",
        "listing:create:owned",
        "listing:delete:owned",
        "listing:edit:owned",
        "listing:view:owned",
        "profile:edit:self",
        "profile:view:self",
        "property:create:self",
        "property:edit:owned",
        "property:view:owned",
        "session:revoke:self",
        "session:view:self",
        "verification:create:self",
        "viewing:manage:assigned",
    ),
    "real_estate_agent": (
        "account:view:self",
        "conversation:view:participant",
        "enquiry:view:assigned",
        "listing:edit:assigned",
        "listing:view:assigned",
        "profile:view:self",
        "property:view:assigned",
        "session:revoke:self",
        "session:view:self",
        "viewing:manage:assigned",
    ),
    "property_manager": (
        "account:view:self",
        "document:view:assigned",
        "maintenance:manage:assigned",
        "portfolio:view:assigned",
        "profile:view:self",
        "property:edit:assigned",
        "property:view:assigned",
        "service_provider:view:assigned",
        "session:revoke:self",
        "session:view:self",
        "tenant:view:assigned",
        "viewing:manage:assigned",
    ),
    "service_provider": (
        "account:view:self",
        "booking:view:assigned",
        "customer:view:booking_participant",
        "payment_record:view:booking_participant",
        "profile:edit:self",
        "profile:view:self",
        "review:view:self",
        "service:create:self",
        "service:edit:self",
        "service:view:self",
        "session:revoke:self",
        "session:view:self",
        "verification:create:self",
    ),
    "moderator": (
        "account:view:self",
        "audit:view:moderation",
        "escalation:create:assigned",
        "moderation:approve:reported",
        "moderation:reject:reported",
        "moderation:view:reported",
        "profile:view:self",
        "report:view:assigned",
        "session:revoke:self",
        "session:view:self",
    ),
    "admin": (
        "account:view:self",
        "analytics:view:platform",
        "audit:view:administrative_workflow",
        "category:manage:global",
        "listing:manage:platform",
        "listing:view:platform",
        "location:manage:global",
        "moderation:view:assigned",
        "profile:view:self",
        "report:view:assigned",
        "roles:assign:operational",
        "session:revoke:self",
        "session:view:self",
        "support:manage:assigned",
        "user:edit:basic",
        "user:view:basic",
        "verification:approve:assigned",
        "verification:reject:assigned",
    ),
    "super_admin": (
        "account:view:self",
        "analytics:view:platform",
        "audit:view:administrative_workflow",
        "category:manage:global",
        "integrations:manage:global",
        "listing:manage:platform",
        "listing:view:platform",
        "location:manage:global",
        "moderation:view:assigned",
        "profile:view:self",
        "report:view:assigned",
        "roles:assign:administrative",
        "roles:assign:operational",
        "roles:revoke:global",
        "roles:view:global",
        "security:manage:global",
        "session:revoke:self",
        "session:view:self",
        "support:manage:assigned",
        "system:manage:global",
        "user:edit:basic",
        "user:view:basic",
        "verification:approve:assigned",
        "verification:reject:assigned",
    ),
}


def _stable_id(kind: str, code: str) -> uuid.UUID:
    return uuid.uuid5(_SEED_NAMESPACE, f"{kind}:{code}")


def _seed_rbac(connection: sa.Connection) -> None:
    """Seed the immutable phase-3 role catalog idempotently."""

    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
        sa.column("granted_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)

    role_ids = dict(connection.execute(sa.select(roles.c.code, roles.c.id)).all())
    for code, name, description in _ROLES:
        if code not in role_ids:
            role_id = _stable_id("role", code)
            connection.execute(
                sa.insert(roles).values(
                    id=role_id,
                    code=code,
                    name=name,
                    description=description,
                    created_at=now,
                )
            )
            role_ids[code] = role_id

    permission_codes = sorted({code for codes in _ROLE_PERMISSIONS.values() for code in codes})
    permission_ids = dict(connection.execute(sa.select(permissions.c.code, permissions.c.id)).all())
    for code in permission_codes:
        if code not in permission_ids:
            resource, action, scope = code.split(":", maxsplit=2)
            description = (
                f"{action.replace('_', ' ').title()} {resource.replace('_', ' ')} in {scope} scope."
            )
            permission_id = _stable_id("permission", code)
            connection.execute(
                sa.insert(permissions).values(
                    id=permission_id,
                    code=code,
                    description=description,
                    created_at=now,
                )
            )
            permission_ids[code] = permission_id

    existing_grants = set(
        connection.execute(
            sa.select(role_permissions.c.role_id, role_permissions.c.permission_id)
        ).all()
    )
    for role_code, permission_codes_for_role in _ROLE_PERMISSIONS.items():
        for permission_code in permission_codes_for_role:
            pair = (role_ids[role_code], permission_ids[permission_code])
            if pair not in existing_grants:
                connection.execute(
                    sa.insert(role_permissions).values(
                        role_id=pair[0],
                        permission_id=pair[1],
                        granted_at=now,
                    )
                )


def upgrade() -> None:
    op.create_table(
        "login_throttles",
        sa.Column("identity_hash", sa.String(length=64), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("identity_hash", name=op.f("pk_login_throttles")),
    )
    op.create_table(
        "account_action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "purpose IN ('email_verification', 'password_reset')",
            name=op.f("ck_account_action_tokens_valid_account_action_purpose"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_account_action_tokens_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_account_action_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_account_action_tokens_token_hash")),
    )
    op.create_index(
        "ix_account_action_tokens_expires", "account_action_tokens", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_account_action_tokens_user_purpose",
        "account_action_tokens",
        ["user_id", "purpose"],
        unique=False,
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_auth_sessions_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_auth_sessions_refresh_token_hash")),
    )
    op.create_index("ix_auth_sessions_user_expires", "auth_sessions", ["user_id", "expires_at"])
    with op.batch_alter_table("permissions") as batch_op:
        batch_op.alter_column(
            "code",
            existing_type=sa.String(length=100),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True)
        )
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("requested_role_code", sa.String(length=64), nullable=True))
    with op.batch_alter_table("user_role_assignments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "scope_type",
                sa.String(length=32),
                nullable=False,
                server_default="global",
            )
        )
        batch_op.add_column(
            sa.Column(
                "scope_id",
                sa.String(length=128),
                nullable=False,
                server_default="*",
            )
        )
        batch_op.drop_constraint(op.f("pk_user_role_assignments"), type_="primary")
        batch_op.create_primary_key(
            op.f("pk_user_role_assignments"),
            ["user_id", "role_id", "scope_type", "scope_id"],
        )
        batch_op.create_check_constraint(
            "valid_role_assignment_scope",
            "(scope_type = 'global' AND scope_id = '*') OR "
            "(scope_type <> 'global' AND scope_id <> '*')",
        )

    _seed_rbac(op.get_bind())


def downgrade() -> None:
    with op.batch_alter_table("user_role_assignments") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_user_role_assignments_valid_role_assignment_scope"), type_="check"
        )
        batch_op.drop_constraint(op.f("pk_user_role_assignments"), type_="primary")
        batch_op.create_primary_key(op.f("pk_user_role_assignments"), ["user_id", "role_id"])
        batch_op.drop_column("scope_id")
        batch_op.drop_column("scope_type")
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("requested_role_code")
    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.drop_column("phone_verified_at")
        batch_op.drop_column("email_verified_at")
        batch_op.drop_column("password_hash")
    with op.batch_alter_table("permissions") as batch_op:
        batch_op.alter_column(
            "code",
            existing_type=sa.String(length=120),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
    op.drop_index("ix_auth_sessions_user_expires", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_account_action_tokens_user_purpose", table_name="account_action_tokens")
    op.drop_index("ix_account_action_tokens_expires", table_name="account_action_tokens")
    op.drop_table("account_action_tokens")
    op.drop_table("login_throttles")
