"""Add retry-safe identifiers to manually recorded savings contributions.

Revision ID: e43a91c7b205
Revises: d14a9c2e5f81
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e43a91c7b205"
down_revision: str | None = "d14a9c2e5f81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("savings_contributions") as batch_op:
        batch_op.add_column(sa.Column("request_id", sa.Uuid(), nullable=True))
        batch_op.create_unique_constraint(
            "uq_savings_contribution_request",
            ["goal_id", "contributor_user_id", "request_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("savings_contributions") as batch_op:
        batch_op.drop_constraint("uq_savings_contribution_request", type_="unique")
        batch_op.drop_column("request_id")
