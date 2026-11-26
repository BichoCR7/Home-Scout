"""phase10

Revision ID: dd6548872d4f
Revises: 20261123_09
Create Date: 2026-11-24 02:23:38.744868
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "dd6548872d4f"
down_revision: str | None = "20261123_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PERMISSION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "homescout:phase-10:rbac-v1")
_NEW_ROLE_PERMISSIONS = {
    "tenant": (
        "conversation:send:participant",
        "roommate:connect:public",
        "roommate:manage:self",
        "roommate:search:public",
        "shared_group:create:self",
        "shared_group:manage:owned",
        "shared_search:manage:member",
        "viewing:create:self",
        "viewing:view:participant",
    ),
    "roommate": (
        "conversation:send:participant",
        "roommate:connect:public",
        "roommate:manage:self",
        "roommate:search:public",
        "shared_group:create:self",
        "shared_group:manage:owned",
        "shared_search:manage:member",
        "viewing:create:self",
        "viewing:view:participant",
    ),
    "landlord": (
        "conversation:send:participant",
        "shared_search:manage:member",
        "viewing:view:participant",
    ),
    "real_estate_agent": (
        "conversation:send:participant",
        "shared_search:manage:member",
        "viewing:view:participant",
    ),
    "property_manager": (
        "conversation:send:participant",
        "shared_search:manage:member",
        "viewing:view:participant",
    ),
    "service_provider": ("conversation:send:participant", "shared_search:manage:member"),
}


def _phase10_permission_id(code: str) -> uuid.UUID:
    return uuid.uuid5(_PERMISSION_NAMESPACE, code)


def _seed_phase10_permissions() -> None:
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
            permission_id = _phase10_permission_id(code)
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
        if role_id is None:
            continue
        for code in codes:
            permission_id = permission_ids[code]
            exists = connection.execute(
                sa.select(grants.c.role_id).where(
                    grants.c.role_id == role_id, grants.c.permission_id == permission_id
                )
            ).first()
            if exists is None:
                connection.execute(
                    grants.insert().values(
                        role_id=role_id, permission_id=permission_id, granted_at=now
                    )
                )


def _remove_phase10_permissions() -> None:
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
            permission_ids = list(
                connection.scalars(sa.select(permissions.c.id).where(permissions.c.code.in_(codes)))
            )
            if permission_ids:
                connection.execute(
                    grants.delete().where(
                        grants.c.role_id == role_id, grants.c.permission_id.in_(permission_ids)
                    )
                )
    for code in all_codes:
        connection.execute(
            permissions.delete().where(permissions.c.id == _phase10_permission_id(code))
        )


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "collaboration_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_collaboration_groups_created_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collaboration_groups")),
    )
    with op.batch_alter_table("collaboration_groups", schema=None) as batch_op:
        batch_op.create_index(
            "ix_collaboration_groups_creator_updated",
            ["created_by_user_id", "updated_at"],
            unique=False,
        )

    op.create_table(
        "comparison_boards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_comparison_boards_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comparison_boards")),
    )
    with op.batch_alter_table("comparison_boards", schema=None) as batch_op:
        batch_op.create_index(
            "ix_comparison_boards_owner_updated", ["owner_user_id", "updated_at"], unique=False
        )

    op.create_table(
        "conversation_blocks",
        sa.Column("blocker_user_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "blocker_user_id <> blocked_user_id",
            name=op.f("ck_conversation_blocks_conversation_block_distinct_users"),
        ),
        sa.ForeignKeyConstraint(
            ["blocked_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_conversation_blocks_blocked_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocker_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_conversation_blocks_blocker_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "blocker_user_id", "blocked_user_id", name=op.f("pk_conversation_blocks")
        ),
    )
    op.create_table(
        "roommate_interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'withdrawn')",
            name=op.f("ck_roommate_interests_roommate_interest_status"),
        ),
        sa.CheckConstraint(
            "requester_user_id <> target_user_id",
            name=op.f("ck_roommate_interests_roommate_interest_distinct_users"),
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_roommate_interests_requester_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_roommate_interests_target_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roommate_interests")),
        sa.UniqueConstraint(
            "requester_user_id", "target_user_id", name="uq_roommate_interest_pair"
        ),
    )
    with op.batch_alter_table("roommate_interests", schema=None) as batch_op:
        batch_op.create_index(
            "ix_roommate_interests_target_status", ["target_user_id", "status"], unique=False
        )

    op.create_table(
        "collaboration_group_members",
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("invited_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('owner', 'member')",
            name=op.f("ck_collaboration_group_members_collaboration_member_role"),
        ),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'declined', 'revoked')",
            name=op.f("ck_collaboration_group_members_collaboration_member_status"),
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_collaboration_group_members_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_collaboration_group_members_invited_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_collaboration_group_members_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("group_id", "user_id", name=op.f("pk_collaboration_group_members")),
    )
    with op.batch_alter_table("collaboration_group_members", schema=None) as batch_op:
        batch_op.create_index(
            "ix_collaboration_group_members_user_status", ["user_id", "status"], unique=False
        )

    op.create_table(
        "shared_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("property_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_comparisons_created_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_shared_comparisons_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_comparisons")),
    )
    with op.batch_alter_table("shared_comparisons", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shared_comparisons_group_created", ["group_id", "created_at"], unique=False
        )

    op.create_table(
        "shared_move_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("encrypted_target_amount", sa.LargeBinary(), nullable=True),
        sa.Column("amount_share_consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_shared_move_goals_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_move_goals_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_move_goals")),
    )
    with op.batch_alter_table("shared_move_goals", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shared_move_goals_group_date", ["group_id", "target_date"], unique=False
        )

    op.create_table(
        "shared_searches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_searches_created_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_shared_searches_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_searches")),
    )
    with op.batch_alter_table("shared_searches", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shared_searches_group_updated", ["group_id", "updated_at"], unique=False
        )

    op.create_table(
        "shared_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('open', 'done', 'cancelled')",
            name=op.f("ck_shared_tasks_shared_task_status"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_tasks_assigned_to_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_tasks_created_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_shared_tasks_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_tasks")),
    )
    with op.batch_alter_table("shared_tasks", schema=None) as batch_op:
        batch_op.create_index("ix_shared_tasks_group_due", ["group_id", "due_at"], unique=False)

    op.create_table(
        "roommate_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_alias", sa.String(length=80), nullable=False),
        sa.Column("about", sa.String(length=500), nullable=True),
        sa.Column("budget_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("budget_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("county_id", sa.Uuid(), nullable=True),
        sa.Column("town_id", sa.Uuid(), nullable=True),
        sa.Column("preferred_move_in", sa.Date(), nullable=True),
        sa.Column("lifestyle_tags", sa.JSON(), nullable=False),
        sa.Column("matching_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "budget_max IS NULL OR budget_max >= 0",
            name=op.f("ck_roommate_profiles_roommate_budget_max"),
        ),
        sa.CheckConstraint(
            "budget_min IS NULL OR budget_max IS NULL OR budget_min <= budget_max",
            name=op.f("ck_roommate_profiles_roommate_budget_order"),
        ),
        sa.CheckConstraint(
            "budget_min IS NULL OR budget_min >= 0",
            name=op.f("ck_roommate_profiles_roommate_budget_min"),
        ),
        sa.ForeignKeyConstraint(
            ["county_id"],
            ["counties.id"],
            name=op.f("fk_roommate_profiles_county_id_counties"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["town_id"],
            ["towns.id"],
            name=op.f("fk_roommate_profiles_town_id_towns"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_roommate_profiles_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roommate_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_roommate_profiles_user_id")),
    )
    with op.batch_alter_table("roommate_profiles", schema=None) as batch_op:
        batch_op.create_index(
            "ix_roommate_profiles_search",
            ["matching_enabled", "county_id", "town_id"],
            unique=False,
        )

    op.create_table(
        "shared_move_goal_consents",
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["shared_move_goals.id"],
            name=op.f("fk_shared_move_goal_consents_goal_id_shared_move_goals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_move_goal_consents_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("goal_id", "user_id", name=op.f("pk_shared_move_goal_consents")),
    )
    op.create_table(
        "comparison_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("encrypted_user_data", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "position >= 0 AND position < 5",
            name=op.f("ck_comparison_items_comparison_item_position"),
        ),
        sa.ForeignKeyConstraint(
            ["board_id"],
            ["comparison_boards.id"],
            name=op.f("fk_comparison_items_board_id_comparison_boards"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_comparison_items_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comparison_items")),
        sa.UniqueConstraint("board_id", "position", name="uq_comparison_item_position"),
        sa.UniqueConstraint("board_id", "property_id", name="uq_comparison_item_property"),
    )
    with op.batch_alter_table("comparison_items", schema=None) as batch_op:
        batch_op.create_index(
            "ix_comparison_items_board_position", ["board_id", "position"], unique=False
        )

    op.create_table(
        "shared_properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["added_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_properties_added_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_shared_properties_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_shared_properties_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_properties")),
        sa.UniqueConstraint("group_id", "property_id", name="uq_shared_properties_group_property"),
    )
    with op.batch_alter_table("shared_properties", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shared_properties_group_added", ["group_id", "created_at"], unique=False
        )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_enquiry_id", sa.Uuid(), nullable=True),
        sa.Column("roommate_interest_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(property_enquiry_id IS NOT NULL AND roommate_interest_id IS NULL "
            "AND group_id IS NULL) OR "
            "(property_enquiry_id IS NULL AND roommate_interest_id IS NOT NULL "
            "AND group_id IS NULL) OR "
            "(property_enquiry_id IS NULL AND roommate_interest_id IS NULL "
            "AND group_id IS NOT NULL)",
            name=op.f("ck_conversations_conversation_context_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_conversations_created_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["collaboration_groups.id"],
            name=op.f("fk_conversations_group_id_collaboration_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["property_enquiry_id"],
            ["property_enquiries.id"],
            name=op.f("fk_conversations_property_enquiry_id_property_enquiries"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["roommate_interest_id"],
            ["roommate_interests.id"],
            name=op.f("fk_conversations_roommate_interest_id_roommate_interests"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
        sa.UniqueConstraint("group_id", name="uq_conversation_group"),
        sa.UniqueConstraint("property_enquiry_id", name="uq_conversation_enquiry"),
        sa.UniqueConstraint("roommate_interest_id", name="uq_conversation_roommate_interest"),
    )
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.create_index("ix_conversations_last_message", ["last_message_at"], unique=False)

    op.create_table(
        "scheduled_viewings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("host_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("request_message", sa.String(length=1000), nullable=True),
        sa.Column("host_message", sa.String(length=1000), nullable=True),
        sa.Column("safe_viewing_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'confirmed', 'reschedule_proposed', 'declined', "
            "'cancelled', 'completed')",
            name=op.f("ck_scheduled_viewings_scheduled_viewing_status"),
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_scheduled_viewings_host_user_id_user_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_scheduled_viewings_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_scheduled_viewings_requester_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["safe_viewing_id"],
            ["safe_viewings.id"],
            name=op.f("fk_scheduled_viewings_safe_viewing_id_safe_viewings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_viewings")),
    )
    with op.batch_alter_table("scheduled_viewings", schema=None) as batch_op:
        batch_op.create_index(
            "ix_scheduled_viewings_host_time", ["host_user_id", "requested_at"], unique=False
        )
        batch_op.create_index(
            "ix_scheduled_viewings_requester_time",
            ["requester_user_id", "requested_at"],
            unique=False,
        )

    op.create_table(
        "shared_property_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shared_property_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_property_comments_author_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shared_property_id"],
            ["shared_properties.id"],
            name=op.f("fk_shared_property_comments_shared_property_id_shared_properties"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_property_comments")),
    )
    with op.batch_alter_table("shared_property_comments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_shared_property_comments_property_created",
            ["shared_property_id", "created_at"],
            unique=False,
        )

    op.create_table(
        "shared_property_votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shared_property_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("vote", sa.String(length=12), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "vote IN ('interested', 'unsure', 'pass')",
            name=op.f("ck_shared_property_votes_shared_property_vote_value"),
        ),
        sa.ForeignKeyConstraint(
            ["shared_property_id"],
            ["shared_properties.id"],
            name=op.f("fk_shared_property_votes_shared_property_id_shared_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_shared_property_votes_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shared_property_votes")),
        sa.UniqueConstraint("shared_property_id", "user_id", name="uq_shared_property_vote_user"),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_body", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_messages_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_conversation_messages_sender_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_messages")),
    )
    with op.batch_alter_table("conversation_messages", schema=None) as batch_op:
        batch_op.create_index(
            "ix_conversation_messages_sender_created",
            ["sender_user_id", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_conversation_messages_thread_created",
            ["conversation_id", "created_at"],
            unique=False,
        )

    op.create_table(
        "conversation_participants",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name=op.f("fk_conversation_participants_conversation_id_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name=op.f("fk_conversation_participants_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "conversation_id", "user_id", name=op.f("pk_conversation_participants")
        ),
    )
    with op.batch_alter_table("conversation_participants", schema=None) as batch_op:
        batch_op.create_index(
            "ix_conversation_participants_user_active", ["user_id", "is_active"], unique=False
        )

    op.create_table(
        "viewing_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("viewing_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_viewing_history_actor_user_id_user_accounts"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["viewing_id"],
            ["scheduled_viewings.id"],
            name=op.f("fk_viewing_history_viewing_id_scheduled_viewings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_viewing_history")),
    )
    with op.batch_alter_table("viewing_history", schema=None) as batch_op:
        batch_op.create_index(
            "ix_viewing_history_viewing_created", ["viewing_id", "created_at"], unique=False
        )

    op.create_table(
        "viewing_journals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("viewing_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("encrypted_data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_viewing_journals_owner_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_viewing_journals_property_id_properties"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["viewing_id"],
            ["scheduled_viewings.id"],
            name=op.f("fk_viewing_journals_viewing_id_scheduled_viewings"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_viewing_journals")),
        sa.UniqueConstraint("viewing_id", name=op.f("uq_viewing_journals_viewing_id")),
    )
    with op.batch_alter_table("viewing_journals", schema=None) as batch_op:
        batch_op.create_index(
            "ix_viewing_journals_owner_updated", ["owner_user_id", "updated_at"], unique=False
        )

    op.create_table(
        "message_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("attached_by_user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["attached_by_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_message_attachments_attached_by_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["private_documents.id"],
            name=op.f("fk_message_attachments_document_id_private_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["conversation_messages.id"],
            name=op.f("fk_message_attachments_message_id_conversation_messages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_attachments")),
        sa.UniqueConstraint("message_id", "document_id", name="uq_message_attachment_document"),
    )
    op.create_table(
        "message_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('received', 'reviewed', 'closed')",
            name=op.f("ck_message_reports_message_report_status"),
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["conversation_messages.id"],
            name=op.f("fk_message_reports_message_id_conversation_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_message_reports_reporter_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_reports")),
        sa.UniqueConstraint("message_id", "reporter_user_id", name="uq_message_report_reporter"),
    )
    with op.batch_alter_table("message_reports", schema=None) as batch_op:
        batch_op.create_index(
            "ix_message_reports_status_created", ["status", "created_at"], unique=False
        )

    op.create_table(
        "viewing_journal_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["private_documents.id"],
            name=op.f("fk_viewing_journal_media_document_id_private_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["viewing_journals.id"],
            name=op.f("fk_viewing_journal_media_journal_id_viewing_journals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_viewing_journal_media")),
        sa.UniqueConstraint("journal_id", "document_id", name="uq_viewing_journal_document"),
    )
    op.create_table(
        "viewing_journal_shares",
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("shared_with_user_id", sa.Uuid(), nullable=False),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["journal_id"],
            ["viewing_journals.id"],
            name=op.f("fk_viewing_journal_shares_journal_id_viewing_journals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shared_with_user_id"],
            ["user_accounts.id"],
            name=op.f("fk_viewing_journal_shares_shared_with_user_id_user_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "journal_id", "shared_with_user_id", name=op.f("pk_viewing_journal_shares")
        ),
    )
    _seed_phase10_permissions()

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("viewing_journal_shares")
    op.drop_table("viewing_journal_media")
    with op.batch_alter_table("message_reports", schema=None) as batch_op:
        batch_op.drop_index("ix_message_reports_status_created")

    op.drop_table("message_reports")
    op.drop_table("message_attachments")
    with op.batch_alter_table("viewing_journals", schema=None) as batch_op:
        batch_op.drop_index("ix_viewing_journals_owner_updated")

    op.drop_table("viewing_journals")
    with op.batch_alter_table("viewing_history", schema=None) as batch_op:
        batch_op.drop_index("ix_viewing_history_viewing_created")

    op.drop_table("viewing_history")
    with op.batch_alter_table("conversation_participants", schema=None) as batch_op:
        batch_op.drop_index("ix_conversation_participants_user_active")

    op.drop_table("conversation_participants")
    with op.batch_alter_table("conversation_messages", schema=None) as batch_op:
        batch_op.drop_index("ix_conversation_messages_thread_created")
        batch_op.drop_index("ix_conversation_messages_sender_created")

    op.drop_table("conversation_messages")
    op.drop_table("shared_property_votes")
    with op.batch_alter_table("shared_property_comments", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_property_comments_property_created")

    op.drop_table("shared_property_comments")
    with op.batch_alter_table("scheduled_viewings", schema=None) as batch_op:
        batch_op.drop_index("ix_scheduled_viewings_requester_time")
        batch_op.drop_index("ix_scheduled_viewings_host_time")

    op.drop_table("scheduled_viewings")
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index("ix_conversations_last_message")

    op.drop_table("conversations")
    with op.batch_alter_table("shared_properties", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_properties_group_added")

    op.drop_table("shared_properties")
    with op.batch_alter_table("comparison_items", schema=None) as batch_op:
        batch_op.drop_index("ix_comparison_items_board_position")

    op.drop_table("comparison_items")
    op.drop_table("shared_move_goal_consents")
    with op.batch_alter_table("roommate_profiles", schema=None) as batch_op:
        batch_op.drop_index("ix_roommate_profiles_search")

    op.drop_table("roommate_profiles")
    with op.batch_alter_table("shared_tasks", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_tasks_group_due")

    op.drop_table("shared_tasks")
    with op.batch_alter_table("shared_searches", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_searches_group_updated")

    op.drop_table("shared_searches")
    with op.batch_alter_table("shared_move_goals", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_move_goals_group_date")

    op.drop_table("shared_move_goals")
    with op.batch_alter_table("shared_comparisons", schema=None) as batch_op:
        batch_op.drop_index("ix_shared_comparisons_group_created")

    op.drop_table("shared_comparisons")
    with op.batch_alter_table("collaboration_group_members", schema=None) as batch_op:
        batch_op.drop_index("ix_collaboration_group_members_user_status")

    op.drop_table("collaboration_group_members")
    with op.batch_alter_table("roommate_interests", schema=None) as batch_op:
        batch_op.drop_index("ix_roommate_interests_target_status")

    op.drop_table("roommate_interests")
    op.drop_table("conversation_blocks")
    with op.batch_alter_table("comparison_boards", schema=None) as batch_op:
        batch_op.drop_index("ix_comparison_boards_owner_updated")

    op.drop_table("comparison_boards")
    with op.batch_alter_table("collaboration_groups", schema=None) as batch_op:
        batch_op.drop_index("ix_collaboration_groups_creator_updated")

    op.drop_table("collaboration_groups")
    _remove_phase10_permissions()
    # ### end Alembic commands ###
