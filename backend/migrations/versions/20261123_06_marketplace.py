"""Add HomeScout property marketplace workflows.

Revision ID: 20261123_06
Revises: add5ba78b682
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_06"
down_revision: str | None = "add5ba78b682"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-6:marketplace-v1")
_ROLE_GRANTS = {
    "tenant": (
        "property:save:self",
        "property:compare:public",
        "property:report:self",
        "search:history:self",
        "alert:manage:self",
        "enquiry:create:self",
    ),
    "landlord": (
        "listing:publish:owned",
        "listing:archive:owned",
        "listing:assign:owned",
        "enquiry:manage:assigned",
    ),
    "real_estate_agent": (
        "listing:create:assigned",
        "listing:publish:assigned",
        "listing:archive:assigned",
        "enquiry:manage:assigned",
    ),
    "property_manager": (
        "listing:edit:assigned",
        "listing:publish:assigned",
        "listing:archive:assigned",
        "enquiry:view:assigned",
        "enquiry:manage:assigned",
    ),
}
_NEW_PERMISSION_CODES = {code for codes in _ROLE_GRANTS.values() for code in codes} - {
    "listing:edit:assigned",
    "enquiry:view:assigned",
}


def upgrade() -> None:
    op.add_column("property_media", sa.Column("storage_key", sa.String(length=100)))
    op.add_column("property_media", sa.Column("mime_type", sa.String(length=40)))
    op.add_column("property_media", sa.Column("byte_size", sa.Integer()))
    with op.batch_alter_table("property_media") as batch:
        batch.create_check_constraint(
            "media_byte_size_nonnegative", "byte_size IS NULL OR byte_size > 0"
        )
        batch.create_check_constraint(
            "media_storage_metadata_complete",
            "(storage_key IS NULL AND mime_type IS NULL AND byte_size IS NULL) OR "
            "(storage_key IS NOT NULL AND mime_type IS NOT NULL AND byte_size IS NOT NULL)",
        )
    op.create_table(
        "property_amenities",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("amenity", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("property_id", "amenity"),
    )
    op.create_index(
        "ix_property_amenities_name_property",
        "property_amenities",
        ["amenity", "property_id"],
    )

    connection = op.get_bind()
    properties = sa.table(
        "properties",
        sa.column("id", sa.Uuid()),
        sa.column("amenities", sa.JSON()),
    )
    amenity_table = sa.table(
        "property_amenities",
        sa.column("property_id", sa.Uuid()),
        sa.column("amenity", sa.String()),
    )
    for property_id, amenities in connection.execute(
        sa.select(properties.c.id, properties.c.amenities)
    ):
        if isinstance(amenities, list):
            rows = [
                {"property_id": property_id, "amenity": str(value).strip()}
                for value in dict.fromkeys(amenities)
                if isinstance(value, str) and value.strip()
            ]
            if rows:
                connection.execute(amenity_table.insert(), rows)

    op.create_table(
        "saved_properties",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "property_id"),
    )
    op.create_index(
        "ix_saved_properties_user_created", "saved_properties", ["user_id", "created_at"]
    )
    op.create_table(
        "property_listing_mandates",
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("agent_user_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_user_id", "agent_user_id"),
    )
    op.create_index(
        "ix_listing_mandates_agent_active",
        "property_listing_mandates",
        ["agent_user_id", "is_active"],
    )
    op.create_table(
        "property_search_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_search_history_user_created",
        "property_search_history",
        ["user_id", "created_at"],
    )
    op.create_table(
        "property_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_alerts_user_active", "property_alerts", ["user_id", "is_active"])
    op.create_table(
        "property_enquiries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('new', 'read', 'closed')", name="ck_property_enquiries_enquiry_status"
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["user_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_property_enquiries_recipient_created",
        "property_enquiries",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_property_enquiries_sender_created",
        "property_enquiries",
        ["sender_user_id", "created_at"],
    )
    op.create_table(
        "property_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "reason IN ('inaccurate_details', 'suspected_scam', 'unsafe_or_prohibited', "
            "'duplicate', 'other')",
            name="ck_property_reports_property_report_reason",
        ),
        sa.CheckConstraint(
            "status IN ('received', 'reviewed', 'closed')",
            name="ck_property_reports_property_report_status",
        ),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "reporter_user_id", name="uq_property_report_reporter"),
    )
    op.create_index(
        "ix_property_reports_status_created", "property_reports", ["status", "created_at"]
    )

    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
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
    permission_codes = sorted({code for codes in _ROLE_GRANTS.values() for code in codes})
    permission_ids = dict(connection.execute(sa.select(permissions.c.code, permissions.c.id)).all())
    for code in permission_codes:
        if code not in permission_ids:
            permission_id = uuid.uuid5(_NAMESPACE, code)
            connection.execute(
                permissions.insert().values(
                    id=permission_id,
                    code=code,
                    description="Phase 6 marketplace permission.",
                    created_at=now,
                )
            )
            permission_ids[code] = permission_id
    existing_grants = set(
        connection.execute(
            sa.select(role_permissions.c.role_id, role_permissions.c.permission_id)
        ).all()
    )
    for role_code, codes in _ROLE_GRANTS.items():
        role_id = role_ids.get(role_code)
        if role_id is None:
            continue
        for code in codes:
            pair = (role_id, permission_ids[code])
            if pair not in existing_grants:
                connection.execute(
                    role_permissions.insert().values(
                        role_id=pair[0], permission_id=pair[1], granted_at=now
                    )
                )
                existing_grants.add(pair)


def downgrade() -> None:
    connection = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    role_table = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    role_ids = dict(connection.execute(sa.select(role_table.c.code, role_table.c.id)).all())
    permission_ids_by_code = dict(
        connection.execute(sa.select(permissions.c.code, permissions.c.id)).all()
    )
    for role_code, codes in _ROLE_GRANTS.items():
        role_id = role_ids.get(role_code)
        ids_for_role = [
            permission_ids_by_code[code] for code in codes if code in permission_ids_by_code
        ]
        if role_id is not None and ids_for_role:
            connection.execute(
                role_permissions.delete().where(
                    role_permissions.c.permission_id.in_(ids_for_role),
                    role_permissions.c.role_id == role_id,
                )
            )
    ids = list(
        connection.scalars(
            sa.select(permissions.c.id).where(permissions.c.code.in_(sorted(_NEW_PERMISSION_CODES)))
        )
    )
    if ids:
        connection.execute(permissions.delete().where(permissions.c.id.in_(ids)))

    op.drop_index("ix_property_enquiries_sender_created", table_name="property_enquiries")
    op.drop_index("ix_property_enquiries_recipient_created", table_name="property_enquiries")
    op.drop_table("property_enquiries")
    op.drop_index("ix_property_reports_status_created", table_name="property_reports")
    op.drop_table("property_reports")
    op.drop_index("ix_property_alerts_user_active", table_name="property_alerts")
    op.drop_table("property_alerts")
    op.drop_index("ix_property_search_history_user_created", table_name="property_search_history")
    op.drop_table("property_search_history")
    op.drop_index("ix_saved_properties_user_created", table_name="saved_properties")
    op.drop_table("saved_properties")
    op.drop_index("ix_listing_mandates_agent_active", table_name="property_listing_mandates")
    op.drop_table("property_listing_mandates")
    op.drop_index("ix_property_amenities_name_property", table_name="property_amenities")
    op.drop_table("property_amenities")
    with op.batch_alter_table("property_media") as batch:
        batch.drop_constraint("media_storage_metadata_complete", type_="check")
        batch.drop_constraint("media_byte_size_nonnegative", type_="check")
        batch.drop_column("byte_size")
        batch.drop_column("mime_type")
        batch.drop_column("storage_key")
