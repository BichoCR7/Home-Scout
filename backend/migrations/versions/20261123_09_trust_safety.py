"""Add manual verification, fraud review, and safe-viewing workflows.

Revision ID: 20261123_09
Revises: c46199e48c9f
Create Date: 2026-11-23 23:30:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "20261123_09"
down_revision: str | None = "c46199e48c9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _grant(role_codes: tuple[str, ...], permission_codes: tuple[str, ...]) -> None:
    connection = op.get_bind()
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
        sa.column("granted_at", sa.DateTime(timezone=True)),
    )
    role_rows = dict(
        connection.execute(
            sa.select(roles.c.code, roles.c.id).where(roles.c.code.in_(role_codes))
        ).all()
    )
    permission_rows = dict(
        connection.execute(
            sa.select(permissions.c.code, permissions.c.id).where(
                permissions.c.code.in_(permission_codes)
            )
        ).all()
    )
    for role_id in role_rows.values():
        for permission_id in permission_rows.values():
            exists = connection.execute(
                sa.select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).first()
            if exists is None:
                connection.execute(
                    role_permissions.insert().values(
                        role_id=role_id,
                        permission_id=permission_id,
                        granted_at=datetime.now(UTC),
                    )
                )


def _revoke(role_codes: tuple[str, ...], permission_codes: tuple[str, ...]) -> None:
    connection = op.get_bind()
    roles = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()))
    permissions = sa.table(
        "permissions", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    role_ids = list(connection.scalars(sa.select(roles.c.id).where(roles.c.code.in_(role_codes))))
    permission_ids = list(
        connection.scalars(
            sa.select(permissions.c.id).where(permissions.c.code.in_(permission_codes))
        )
    )
    if role_ids and permission_ids:
        connection.execute(
            role_permissions.delete().where(
                role_permissions.c.role_id.in_(role_ids),
                role_permissions.c.permission_id.in_(permission_ids),
            )
        )


def upgrade() -> None:
    # A previous local SQLite attempt may have completed this non-transactional
    # ALTER before a later batch operation failed. Resume safely in that case.
    if "storage_encrypted" not in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("private_documents")
    }:
        op.add_column(
            "private_documents",
            sa.Column(
                "storage_encrypted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    with op.batch_alter_table("properties") as batch:
        batch.drop_constraint(op.f("ck_properties_verification_status"), type_="check")
        batch.add_column(
            sa.Column(
                "moderation_status",
                sa.String(length=24),
                nullable=False,
                server_default="clear",
            )
        )
        batch.create_check_constraint(
            op.f("ck_properties_verification_status"),
            "verification_status IN ('not_submitted', 'pending', 'verified', "
            "'rejected', 'expired')",
        )
        batch.create_check_constraint(
            op.f("ck_properties_moderation_status"),
            "moderation_status IN ('clear', 'under_review', 'removed')",
        )

    with op.batch_alter_table("property_reports") as batch:
        batch.drop_constraint(
            op.f("ck_property_reports_ck_property_reports_property_report_status"),
            type_="check",
        )
        batch.add_column(sa.Column("encrypted_details", sa.LargeBinary(), nullable=True))
        batch.add_column(sa.Column("staff_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("resolution_message", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            op.f("fk_property_reports_reviewed_by_user_id_user_accounts"),
            "user_accounts",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_check_constraint(
            op.f("ck_property_reports_property_report_status"),
            "status IN ('received', 'reviewed', 'closed', 'in_review', 'escalated', "
            "'resolved', 'dismissed')",
        )
    op.execute(
        sa.text("UPDATE property_reports SET updated_at = created_at WHERE updated_at IS NULL")
    )
    with op.batch_alter_table("property_reports") as batch:
        batch.alter_column("updated_at", nullable=False)

    op.create_table(
        "verification_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=24), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=True),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("submission_number", sa.Integer(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(subject_type = 'property' AND property_id IS NOT NULL AND "
            "subject_user_id IS NULL) OR "
            "(subject_type <> 'property' AND subject_user_id IS NOT NULL AND property_id IS NULL)",
            name=op.f("ck_verification_cases_verification_subject_shape"),
        ),
        sa.CheckConstraint(
            "subject_type IN ('landlord', 'agent', 'property', 'service_provider')",
            name=op.f("ck_verification_cases_verification_subject_type"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name=op.f("ck_verification_cases_verification_case_status"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_verification_cases"),
    )
    op.create_index(
        "ix_verification_cases_status_submitted", "verification_cases", ["status", "submitted_at"]
    )
    op.create_index(
        "ix_verification_cases_owner_updated", "verification_cases", ["owner_user_id", "updated_at"]
    )

    op.create_table(
        "verification_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("submission_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["private_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_verification_evidence"),
        sa.UniqueConstraint(
            "case_id",
            "submission_number",
            "document_id",
            name="uq_verification_evidence_submission_doc",
        ),
    )
    op.create_index(
        "ix_verification_evidence_case_submission",
        "verification_evidence",
        ["case_id", "submission_number"],
    )

    op.create_table(
        "verification_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("submission_number", sa.Integer(), nullable=False),
        sa.Column("encrypted_note", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('submitted', 'resubmitted', 'approved', 'rejected', 'expired')",
            name=op.f("ck_verification_history_verification_history_action"),
        ),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_verification_history"),
    )
    op.create_index(
        "ix_verification_history_case_created", "verification_history", ["case_id", "created_at"]
    )

    op.create_table(
        "safe_viewings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("shared_with_user_id", sa.Uuid(), nullable=True),
        sa.Column("details_share_consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encrypted_data", sa.LargeBinary(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('planned', 'checked_in', 'checked_out', 'cancelled')",
            name=op.f("ck_safe_viewings_safe_viewing_status"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shared_with_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_safe_viewings"),
    )
    op.create_index("ix_safe_viewings_owner_start", "safe_viewings", ["owner_user_id", "starts_at"])
    op.create_index(
        "ix_safe_viewings_shared_start", "safe_viewings", ["shared_with_user_id", "starts_at"]
    )

    op.create_table(
        "safety_incident_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("viewing_id", sa.Uuid(), nullable=True),
        sa.Column("property_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("encrypted_details", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("staff_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('viewing_safety', 'impersonation', 'pressure_or_threat', "
            "'payment_request', 'privacy', 'other')",
            name=op.f("ck_safety_incident_reports_safety_report_category"),
        ),
        sa.CheckConstraint(
            "status IN ('received', 'in_review', 'escalated', 'resolved', 'dismissed')",
            name=op.f("ck_safety_incident_reports_safety_report_status"),
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["viewing_id"], ["safe_viewings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_safety_incident_reports"),
    )
    op.create_index(
        "ix_safety_incident_reports_status_created",
        "safety_incident_reports",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_safety_incident_reports_owner_created",
        "safety_incident_reports",
        ["owner_user_id", "created_at"],
    )

    op.create_table(
        "trust_report_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("listing_report_id", sa.Uuid(), nullable=True),
        sa.Column("incident_report_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(listing_report_id IS NOT NULL AND incident_report_id IS NULL) OR "
            "(listing_report_id IS NULL AND incident_report_id IS NOT NULL)",
            name=op.f("ck_trust_report_evidence_trust_report_evidence_target"),
        ),
        sa.ForeignKeyConstraint(["listing_report_id"], ["property_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["incident_report_id"], ["safety_incident_reports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["private_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_trust_report_evidence"),
        sa.UniqueConstraint(
            "listing_report_id", "document_id", name="uq_trust_evidence_listing_doc"
        ),
        sa.UniqueConstraint(
            "incident_report_id", "document_id", name="uq_trust_evidence_incident_doc"
        ),
    )
    op.create_index(
        "ix_trust_report_evidence_listing", "trust_report_evidence", ["listing_report_id"]
    )
    op.create_index(
        "ix_trust_report_evidence_incident", "trust_report_evidence", ["incident_report_id"]
    )

    op.create_table(
        "safety_incident_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('submitted', 'in_review', 'escalated', 'resolved', 'dismissed')",
            name=op.f("ck_safety_incident_history_safety_incident_history_action"),
        ),
        sa.ForeignKeyConstraint(["report_id"], ["safety_incident_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_safety_incident_history"),
    )
    op.create_index(
        "ix_safety_incident_history_report_created",
        "safety_incident_history",
        ["report_id", "created_at"],
    )

    op.create_table(
        "property_report_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("public_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('in_review', 'escalated', 'resolved', 'dismissed')",
            name=op.f("ck_property_report_reviews_property_report_review_action"),
        ),
        sa.ForeignKeyConstraint(["report_id"], ["property_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_property_report_reviews"),
    )
    op.create_index(
        "ix_property_report_reviews_report_created",
        "property_report_reviews",
        ["report_id", "created_at"],
    )

    _grant(
        ("landlord", "real_estate_agent", "service_provider"),
        ("verification:create:self",),
    )
    _grant(
        ("admin", "super_admin"),
        (
            "verification:approve:assigned",
            "verification:reject:assigned",
            "moderation:view:assigned",
            "moderation:approve:reported",
            "moderation:reject:reported",
            "escalation:create:assigned",
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE property_reports SET status = CASE "
            "WHEN status IN ('in_review', 'escalated', 'resolved') THEN 'reviewed' "
            "WHEN status = 'dismissed' THEN 'closed' ELSE status END"
        )
    )
    op.drop_index("ix_property_report_reviews_report_created", table_name="property_report_reviews")
    op.drop_table("property_report_reviews")
    op.drop_index("ix_safety_incident_history_report_created", table_name="safety_incident_history")
    op.drop_table("safety_incident_history")
    op.drop_index("ix_trust_report_evidence_incident", table_name="trust_report_evidence")
    op.drop_index("ix_trust_report_evidence_listing", table_name="trust_report_evidence")
    op.drop_table("trust_report_evidence")
    op.drop_index("ix_safety_incident_reports_owner_created", table_name="safety_incident_reports")
    op.drop_index("ix_safety_incident_reports_status_created", table_name="safety_incident_reports")
    op.drop_table("safety_incident_reports")
    op.drop_index("ix_safe_viewings_shared_start", table_name="safe_viewings")
    op.drop_index("ix_safe_viewings_owner_start", table_name="safe_viewings")
    op.drop_table("safe_viewings")
    op.drop_index("ix_verification_history_case_created", table_name="verification_history")
    op.drop_table("verification_history")
    op.drop_index("ix_verification_evidence_case_submission", table_name="verification_evidence")
    op.drop_table("verification_evidence")
    op.drop_index("ix_verification_cases_owner_updated", table_name="verification_cases")
    op.drop_index("ix_verification_cases_status_submitted", table_name="verification_cases")
    op.drop_table("verification_cases")

    with op.batch_alter_table("property_reports") as batch:
        batch.drop_constraint(op.f("ck_property_reports_property_report_status"), type_="check")
        batch.drop_constraint(
            op.f("fk_property_reports_reviewed_by_user_id_user_accounts"),
            type_="foreignkey",
        )
        batch.drop_column("updated_at")
        batch.drop_column("reviewed_by_user_id")
        batch.drop_column("resolution_message")
        batch.drop_column("staff_note")
        batch.drop_column("encrypted_details")
        batch.create_check_constraint(
            op.f("ck_property_reports_property_report_status"),
            "status IN ('received', 'reviewed', 'closed')",
        )

    op.execute(
        sa.text(
            "UPDATE properties SET verification_status = 'rejected' "
            "WHERE verification_status = 'expired'"
        )
    )
    with op.batch_alter_table("properties") as batch:
        batch.drop_constraint(op.f("ck_properties_moderation_status"), type_="check")
        batch.drop_constraint(op.f("ck_properties_verification_status"), type_="check")
        batch.drop_column("moderation_status")
        batch.create_check_constraint(
            op.f("ck_properties_verification_status"),
            "verification_status IN ('not_submitted', 'pending', 'verified', 'rejected')",
        )

    _revoke(("real_estate_agent",), ("verification:create:self",))
    _revoke(
        ("admin", "super_admin"),
        (
            "moderation:approve:reported",
            "moderation:reject:reported",
            "escalation:create:assigned",
        ),
    )
