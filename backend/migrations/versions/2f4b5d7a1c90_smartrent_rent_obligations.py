"""Add encrypted rent obligations and user-reported payment records.

Revision ID: 2f4b5d7a1c90
Revises: e43a91c7b205
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f4b5d7a1c90"
down_revision: str | None = "e43a91c7b205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rent_obligations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("encrypted_data", sa.LargeBinary(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('open', 'cancelled')", name="rent_obligation_status"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "owner_user_id", name="uq_rent_obligation_id_owner"),
    )
    op.create_index(
        "ix_rent_obligations_owner_status",
        "rent_obligations",
        ["owner_user_id", "status", "due_date"],
    )
    op.create_table(
        "rent_payment_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("obligation_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["obligation_id", "owner_user_id"],
            ["rent_obligations.id", "rent_obligations.owner_user_id"],
            name="fk_rent_payment_record_owned_obligation",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "request_id", name="uq_rent_payment_owner_request"),
    )
    op.create_index(
        "ix_rent_payment_records_owner_created",
        "rent_payment_records",
        ["owner_user_id", "created_at"],
    )
    op.create_index(
        "ix_rent_payment_records_obligation",
        "rent_payment_records",
        ["obligation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rent_payment_records_obligation", table_name="rent_payment_records")
    op.drop_index("ix_rent_payment_records_owner_created", table_name="rent_payment_records")
    op.drop_table("rent_payment_records")
    op.drop_index("ix_rent_obligations_owner_status", table_name="rent_obligations")
    op.drop_table("rent_obligations")
