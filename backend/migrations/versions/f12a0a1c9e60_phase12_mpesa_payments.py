"""Phase 12 M-Pesa transaction records and payment permissions.

Revision ID: f12a0a1c9e60
Revises: 74f53d9373ba
Create Date: 2026-11-24
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "f12a0a1c9e60"
down_revision: str | None = "74f53d9373ba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-12:rbac-v1")
_ROLE_PERMISSIONS = {
    "tenant": ("payment:create:self", "payment:view:self"),
    "roommate": ("payment:create:self", "payment:view:self"),
    "service_provider": ("payment:view:booking_participant",),
    "admin": ("payment:view:global", "payment:reconcile:global"),
    "super_admin": ("payment:view:global", "payment:reconcile:global"),
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
    all_codes = sorted({permission for codes in _ROLE_PERMISSIONS.values() for permission in codes})
    existing = dict(
        connection.execute(
            sa.select(permissions.c.code, permissions.c.id).where(permissions.c.code.in_(all_codes))
        ).all()
    )
    for code in all_codes:
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
    for role_code, codes in _ROLE_PERMISSIONS.items():
        role_id = role_ids.get(role_code)
        if role_id is None:
            continue
        for code in codes:
            permission_id = existing[code]
            grant_exists = connection.execute(
                sa.select(grants.c.role_id).where(
                    grants.c.role_id == role_id,
                    grants.c.permission_id == permission_id,
                )
            ).first()
            if grant_exists is None:
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
    codes = sorted({permission for values in _ROLE_PERMISSIONS.values() for permission in values})
    role_ids = list(
        connection.scalars(sa.select(roles.c.id).where(roles.c.code.in_(_ROLE_PERMISSIONS)))
    )
    permission_ids = list(
        connection.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes)))
    )
    if role_ids and permission_ids:
        connection.execute(
            grants.delete().where(
                grants.c.role_id.in_(role_ids), grants.c.permission_id.in_(permission_ids)
            )
        )
    connection.execute(permissions.delete().where(permissions.c.code.in_(codes)))


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("payer_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("service_order_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("payment_purpose", sa.String(length=40), nullable=False),
        sa.Column("amount_kes", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("environment", sa.String(length=12), nullable=False),
        sa.Column("payer_phone_hmac", sa.String(length=64), nullable=False),
        sa.Column("payer_phone_last4", sa.String(length=4), nullable=False),
        sa.Column("merchant_request_id", sa.String(length=128), nullable=True),
        sa.Column("checkout_request_id", sa.String(length=128), nullable=True),
        sa.Column("receipt_number", sa.String(length=32), nullable=True),
        sa.Column("provider_result_code", sa.String(length=24), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("submission_unknown", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reconciliation_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reconciliation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("currency = 'KES'", name="payment_currency_kes"),
        sa.CheckConstraint("amount_kes > 0", name="payment_amount_positive"),
        sa.CheckConstraint("payment_purpose = 'service_booking'", name="payment_purpose_allowed"),
        sa.CheckConstraint(
            "status IN ('initiated','pending','successful','failed','cancelled','expired',"
            "'reversed')",
            name="payment_status",
        ),
        sa.CheckConstraint("environment IN ('sandbox','production')", name="payment_environment"),
        sa.ForeignKeyConstraint(["payer_user_id"], ["user_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_order_id"], ["service_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "merchant_request_id", name="uq_payment_transactions_merchant_request_id"
        ),
        sa.UniqueConstraint(
            "checkout_request_id", name="uq_payment_transactions_checkout_request_id"
        ),
        sa.UniqueConstraint("receipt_number", name="uq_payment_transactions_receipt_number"),
    )
    op.create_index(
        "ix_payment_transactions_user_created",
        "payment_transactions",
        ["payer_user_id", "created_at"],
    )
    op.create_index(
        "ix_payment_transactions_status_updated",
        "payment_transactions",
        ["status", "updated_at"],
    )
    op.create_index(
        "uq_payment_transactions_user_idempotency",
        "payment_transactions",
        ["payer_user_id", "idempotency_key_hash"],
        unique=True,
    )
    op.create_index(
        "uq_payment_transactions_order_in_flight",
        "payment_transactions",
        ["service_order_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('initiated','pending')"),
        postgresql_where=sa.text("status IN ('initiated','pending')"),
    )
    op.create_index(
        "uq_payment_transactions_order_success",
        "payment_transactions",
        ["service_order_id"],
        unique=True,
        sqlite_where=sa.text("status = 'successful'"),
        postgresql_where=sa.text("status = 'successful'"),
    )
    op.create_table(
        "payment_callback_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("transaction_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("checkout_request_id", sa.String(length=128), nullable=False),
        sa.Column("callback_result_code", sa.String(length=24), nullable=False),
        sa.Column("callback_amount_kes", sa.Numeric(12, 2), nullable=True),
        sa.Column("callback_phone_hmac", sa.String(length=64), nullable=True),
        sa.Column("receipt_candidate", sa.String(length=32), nullable=True),
        sa.Column("transaction_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_status", sa.String(length=12), nullable=False),
        sa.Column("process_code", sa.String(length=64), nullable=True),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "processing_status IN ('pending','processed','rejected')",
            name="payment_callback_processing_status",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["payment_transactions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_digest", name="uq_payment_callback_events_payload_digest"),
    )
    op.create_index(
        "ix_payment_callback_events_transaction",
        "payment_callback_events",
        ["transaction_id", "received_at"],
    )
    _seed_permissions()


def downgrade() -> None:
    _remove_permissions()
    op.drop_index("ix_payment_callback_events_transaction", table_name="payment_callback_events")
    op.drop_table("payment_callback_events")
    op.drop_index("uq_payment_transactions_order_success", table_name="payment_transactions")
    op.drop_index("uq_payment_transactions_order_in_flight", table_name="payment_transactions")
    op.drop_index("uq_payment_transactions_user_idempotency", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_status_updated", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_user_created", table_name="payment_transactions")
    op.drop_table("payment_transactions")
