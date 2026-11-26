"""phase11 services moving and maintenance

Revision ID: 74f53d9373ba
Revises: dd6548872d4f
Create Date: 2026-11-24 04:16:29.942547
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "74f53d9373ba"
down_revision: str | None = "dd6548872d4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None

_PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-11:rbac-v1")
_NEW_ROLE_PERMISSIONS = {
    "tenant": (
        "booking:create:self",
        "maintenance:create:self",
        "maintenance:view:self",
        "move_plan:manage:self",
        "room_setup:manage:self",
        "service_review:create:self",
    ),
    "roommate": (
        "booking:create:self",
        "booking:view:self",
        "maintenance:create:self",
        "maintenance:view:self",
        "move_plan:manage:self",
        "room_setup:manage:self",
        "service_review:create:self",
    ),
    "landlord": ("maintenance:manage:assigned",),
    "real_estate_agent": ("maintenance:manage:assigned",),
    "property_manager": ("maintenance:view:assigned",),
    "service_provider": (
        "booking:manage:assigned",
        "maintenance:view:assigned",
        "order:view:assigned",
    ),
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
    all_codes = sorted({code for codes in _NEW_ROLE_PERMISSIONS.values() for code in codes})
    permission_ids = dict(
        connection.execute(
            sa.select(permissions.c.code, permissions.c.id).where(permissions.c.code.in_(all_codes))
        ).all()
    )
    for code in all_codes:
        if code not in permission_ids:
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
            permission_ids[code] = permission_id
    for role_code, codes in _NEW_ROLE_PERMISSIONS.items():
        role_id = role_ids.get(role_code)
        if role_id is not None:
            for code in codes:
                exists = connection.scalar(
                    sa.select(grants.c.role_id)
                    .where(
                        grants.c.role_id == role_id, grants.c.permission_id == permission_ids[code]
                    )
                    .limit(1)
                )
                if exists is None:
                    connection.execute(
                        grants.insert().values(
                            role_id=role_id, permission_id=permission_ids[code], granted_at=now
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
    role_ids = dict(connection.execute(sa.select(roles.c.code, roles.c.id)).all())
    all_codes = {code for codes in _NEW_ROLE_PERMISSIONS.values() for code in codes}
    for role_code, codes in _NEW_ROLE_PERMISSIONS.items():
        role_id = role_ids.get(role_code)
        if role_id is not None:
            ids = list(
                connection.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes)))
            )
            if ids:
                connection.execute(
                    grants.delete().where(
                        grants.c.role_id == role_id, grants.c.permission_id.in_(ids)
                    )
                )
    for code in all_codes:
        connection.execute(permissions.delete().where(permissions.c.id == _permission_id(code)))


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "move_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("move_date", sa.Date(), nullable=True),
        sa.Column("target_budget_kes", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_move_plans_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_move_plans")),
    )
    with op.batch_alter_table("move_plans", schema=None) as batch_op:
        batch_op.create_index(
            "ix_move_plans_owner_move_date", ["owner_user_id", "move_date"], unique=False
        )

    op.create_table(
        "service_offerings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pricing_model", sa.String(length=12), nullable=False),
        sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("availability_schedule", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('movers','cleaners','plumbers','electricians',"
            "'internet_providers','furniture_providers','handymen','home_maintenance','other')",
            name=op.f("ck_service_offerings_service_category"),
        ),
        sa.CheckConstraint(
            "currency = 'KES'", name=op.f("ck_service_offerings_service_currency_kes")
        ),
        sa.CheckConstraint(
            "pricing_model = 'quote' OR price_amount IS NOT NULL",
            name=op.f("ck_service_offerings_service_price_required"),
        ),
        sa.CheckConstraint(
            "pricing_model IN ('fixed','hourly','from','quote')",
            name=op.f("ck_service_offerings_service_pricing_model"),
        ),
        sa.CheckConstraint(
            "price_amount IS NULL OR price_amount >= 0",
            name=op.f("ck_service_offerings_service_price_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_offerings_provider_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_offerings")),
    )
    with op.batch_alter_table("service_offerings", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_offerings_category_active", ["category", "is_active"], unique=False
        )
        batch_op.create_index(
            "ix_service_offerings_provider_active", ["provider_user_id", "is_active"], unique=False
        )

    op.create_table(
        "service_provider_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("caption", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_provider_images_provider_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_provider_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_service_provider_images_storage_key")),
    )
    with op.batch_alter_table("service_provider_images", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_provider_images_provider", ["provider_user_id", "created_at"], unique=False
        )

    op.create_table(
        "service_provider_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("public_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("availability_note", sa.String(length=300), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_provider_profiles_provider_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_provider_profiles")),
        sa.UniqueConstraint(
            "provider_user_id", name=op.f("uq_service_provider_profiles_provider_user_id")
        ),
    )
    with op.batch_alter_table("service_provider_profiles", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_provider_profiles_public", ["is_published", "updated_at"], unique=False
        )

    op.create_table(
        "move_budget_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("move_plan_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("amount_kes", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("provider_offering_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "amount_kes >= 0", name=op.f("ck_move_budget_items_move_budget_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["move_plan_id"],
            ["move_plans.id"],
            name=op.f("fk_move_budget_items_move_plan_id_move_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_move_budget_items_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_move_budget_items_provider_offering_id_service_offerings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_move_budget_items")),
    )
    op.create_table(
        "room_setup_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("move_plan_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("room_name", sa.String(length=80), nullable=False),
        sa.Column("item_name", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_kes", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned','purchased')", name=op.f("ck_room_setup_items_room_item_status")
        ),
        sa.CheckConstraint(
            "estimated_cost_kes IS NULL OR estimated_cost_kes >= 0",
            name=op.f("ck_room_setup_items_room_item_cost"),
        ),
        sa.CheckConstraint(
            "quantity BETWEEN 1 AND 100", name=op.f("ck_room_setup_items_room_item_quantity")
        ),
        sa.ForeignKeyConstraint(
            ["move_plan_id"],
            ["move_plans.id"],
            name=op.f("fk_room_setup_items_move_plan_id_move_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_room_setup_items_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_room_setup_items")),
    )
    with op.batch_alter_table("room_setup_items", schema=None) as batch_op:
        batch_op.create_index(
            "ix_room_setup_items_plan_room", ["move_plan_id", "room_name"], unique=False
        )

    op.create_table(
        "service_areas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("county_id", sa.Uuid(), nullable=True),
        sa.Column("town_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "town_id IS NOT NULL OR county_id IS NOT NULL",
            name=op.f("ck_service_areas_service_area_location_required"),
        ),
        sa.ForeignKeyConstraint(
            ["county_id"],
            ["counties.id"],
            name=op.f("fk_service_areas_county_id_counties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_service_areas_offering_id_service_offerings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["town_id", "county_id"],
            ["towns.id", "towns.county_id"],
            name="fk_service_areas_town_county",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_areas")),
        sa.UniqueConstraint("offering_id", "county_id", "town_id", name="uq_service_area_location"),
    )
    with op.batch_alter_table("service_areas", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_areas_county_town", ["county_id", "town_id"], unique=False
        )

    op.create_table(
        "maintenance_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("resident_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_manager_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_provider_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_offering_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("completion_record", sa.String(length=1000), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('plumbing','electrical','cleaning','internet',"
            "'appliance','structural','other')",
            name=op.f("ck_maintenance_requests_maintenance_category"),
        ),
        sa.CheckConstraint(
            "priority IN ('low','normal','high','urgent')",
            name=op.f("ck_maintenance_requests_maintenance_priority"),
        ),
        sa.CheckConstraint(
            "status IN ('submitted','assigned','in_progress','completed','cancelled')",
            name=op.f("ck_maintenance_requests_maintenance_status"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_manager_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_maintenance_requests_assigned_manager_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_maintenance_requests_assigned_offering_id_service_offerings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_maintenance_requests_assigned_provider_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_maintenance_requests_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resident_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_maintenance_requests_resident_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_requests")),
    )
    with op.batch_alter_table("maintenance_requests", schema=None) as batch_op:
        batch_op.create_index(
            "ix_maintenance_requests_property_status",
            ["property_id", "status", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_maintenance_requests_provider_status",
            ["assigned_provider_user_id", "status"],
            unique=False,
        )

    op.create_table(
        "property_resident_access",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("resident_user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','revoked')",
            name=op.f("ck_property_resident_access_resident_access_status"),
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_property_resident_access_granted_by_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_property_resident_access_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resident_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_property_resident_access_resident_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_resident_access")),
        sa.UniqueConstraint("property_id", "resident_user_id", name="uq_property_resident"),
    )
    with op.batch_alter_table("property_resident_access", schema=None) as batch_op:
        batch_op.create_index(
            "ix_property_resident_access_resident", ["resident_user_id", "status"], unique=False
        )

    op.create_table(
        "service_bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reschedule_return_status", sa.String(length=16), nullable=True),
        sa.Column("request_details", sa.Text(), nullable=False),
        sa.Column("provider_response", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','reschedule_proposed',"
            "'rescheduled','cancelled','completed')",
            name=op.f("ck_service_bookings_service_booking_status"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_bookings_customer_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_service_bookings_offering_id_service_offerings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_service_bookings_property_id_properties"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_bookings_provider_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_bookings")),
    )
    with op.batch_alter_table("service_bookings", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_bookings_customer_created", ["customer_user_id", "created_at"], unique=False
        )
        batch_op.create_index(
            "ix_service_bookings_provider_status",
            ["provider_user_id", "status", "requested_at"],
            unique=False,
        )

    op.create_table(
        "maintenance_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_maintenance_history_actor_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["maintenance_requests.id"],
            name=op.f("fk_maintenance_history_request_id_maintenance_requests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_history")),
    )
    with op.batch_alter_table("maintenance_history", schema=None) as batch_op:
        batch_op.create_index(
            "ix_maintenance_history_request_created", ["request_id", "created_at"], unique=False
        )

    op.create_table(
        "maintenance_request_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["private_documents.id"],
            name=op.f("fk_maintenance_request_photos_document_id_private_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["maintenance_requests.id"],
            name=op.f("fk_maintenance_request_photos_request_id_maintenance_requests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_request_photos")),
        sa.UniqueConstraint("request_id", "document_id", name="uq_maintenance_photo_document"),
    )
    op.create_table(
        "move_plan_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("move_plan_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("provider_offering_id", sa.Uuid(), nullable=True),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('packing','moving_day','utilities','internet_setup',"
            "'cleaning','furniture','post_move','other')",
            name=op.f("ck_move_plan_tasks_move_task_category"),
        ),
        sa.CheckConstraint(
            "status IN ('open','completed','cancelled')",
            name=op.f("ck_move_plan_tasks_move_task_status"),
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["service_bookings.id"],
            name=op.f("fk_move_plan_tasks_booking_id_service_bookings"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["move_plan_id"],
            ["move_plans.id"],
            name=op.f("fk_move_plan_tasks_move_plan_id_move_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_move_plan_tasks_provider_offering_id_service_offerings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_move_plan_tasks")),
    )
    with op.batch_alter_table("move_plan_tasks", schema=None) as batch_op:
        batch_op.create_index(
            "ix_move_plan_tasks_plan_due", ["move_plan_id", "due_date"], unique=False
        )

    op.create_table(
        "service_booking_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_booking_events_actor_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["service_bookings.id"],
            name=op.f("fk_service_booking_events_booking_id_service_bookings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_booking_events")),
    )
    with op.batch_alter_table("service_booking_events", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_booking_events_booking_created", ["booking_id", "created_at"], unique=False
        )

    op.create_table(
        "service_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("customer_user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("offering_title_snapshot", sa.String(length=140), nullable=False),
        sa.Column("category_snapshot", sa.String(length=32), nullable=False),
        sa.Column("estimated_amount_kes", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("pricing_model_snapshot", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','reschedule_proposed',"
            "'rescheduled','cancelled','completed')",
            name=op.f("ck_service_orders_service_order_status"),
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["service_bookings.id"],
            name=op.f("fk_service_orders_booking_id_service_bookings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_orders_customer_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_orders_provider_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_orders")),
        sa.UniqueConstraint("booking_id", name=op.f("uq_service_orders_booking_id")),
    )
    with op.batch_alter_table("service_orders", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_orders_provider_status",
            ["provider_user_id", "status", "created_at"],
            unique=False,
        )

    op.create_table(
        "service_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_user_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5", name=op.f("ck_service_reviews_service_review_rating")
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["service_bookings.id"],
            name=op.f("fk_service_reviews_booking_id_service_bookings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["service_offerings.id"],
            name=op.f("fk_service_reviews_offering_id_service_offerings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_reviews_provider_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_service_reviews_reviewer_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_reviews")),
        sa.UniqueConstraint("booking_id", name="uq_service_review_booking"),
    )
    with op.batch_alter_table("service_reviews", schema=None) as batch_op:
        batch_op.create_index(
            "ix_service_reviews_offering_created", ["offering_id", "created_at"], unique=False
        )

    _seed_permissions()

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    _remove_permissions()

    with op.batch_alter_table("service_reviews", schema=None) as batch_op:
        batch_op.drop_index("ix_service_reviews_offering_created")

    op.drop_table("service_reviews")
    with op.batch_alter_table("service_orders", schema=None) as batch_op:
        batch_op.drop_index("ix_service_orders_provider_status")

    op.drop_table("service_orders")
    with op.batch_alter_table("service_booking_events", schema=None) as batch_op:
        batch_op.drop_index("ix_service_booking_events_booking_created")

    op.drop_table("service_booking_events")
    with op.batch_alter_table("move_plan_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_move_plan_tasks_plan_due")

    op.drop_table("move_plan_tasks")
    op.drop_table("maintenance_request_photos")
    with op.batch_alter_table("maintenance_history", schema=None) as batch_op:
        batch_op.drop_index("ix_maintenance_history_request_created")

    op.drop_table("maintenance_history")
    with op.batch_alter_table("service_bookings", schema=None) as batch_op:
        batch_op.drop_index("ix_service_bookings_provider_status")
        batch_op.drop_index("ix_service_bookings_customer_created")

    op.drop_table("service_bookings")
    with op.batch_alter_table("property_resident_access", schema=None) as batch_op:
        batch_op.drop_index("ix_property_resident_access_resident")

    op.drop_table("property_resident_access")
    with op.batch_alter_table("maintenance_requests", schema=None) as batch_op:
        batch_op.drop_index("ix_maintenance_requests_provider_status")
        batch_op.drop_index("ix_maintenance_requests_property_status")

    op.drop_table("maintenance_requests")
    with op.batch_alter_table("service_areas", schema=None) as batch_op:
        batch_op.drop_index("ix_service_areas_county_town")

    op.drop_table("service_areas")
    with op.batch_alter_table("room_setup_items", schema=None) as batch_op:
        batch_op.drop_index("ix_room_setup_items_plan_room")

    op.drop_table("room_setup_items")
    op.drop_table("move_budget_items")
    with op.batch_alter_table("service_provider_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_service_provider_profiles_public")

    op.drop_table("service_provider_profiles")
    with op.batch_alter_table("service_provider_images", schema=None) as batch_op:
        batch_op.drop_index("ix_service_provider_images_provider")

    op.drop_table("service_provider_images")
    with op.batch_alter_table("service_offerings", schema=None) as batch_op:
        batch_op.drop_index("ix_service_offerings_provider_active")
        batch_op.drop_index("ix_service_offerings_category_active")

    op.drop_table("service_offerings")
    with op.batch_alter_table("move_plans", schema=None) as batch_op:
        batch_op.drop_index("ix_move_plans_owner_move_date")

    op.drop_table("move_plans")
    # ### end Alembic commands ###
