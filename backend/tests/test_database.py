"""Database initialization, model relation, and SQLite safety tests."""

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_database_engine
from app.models import (
    ApplicationSetting,
    AuditEvent,
    InAppNotification,
    Permission,
    Role,
    RolePermission,
    UserAccount,
    UserProfile,
    UserRoleAssignment,
)

FOUNDATION_TABLES = {
    "application_settings",
    "audit_events",
    "in_app_notifications",
    "permissions",
    "role_permissions",
    "roles",
    "user_accounts",
    "user_profiles",
    "user_role_assignments",
}


def test_database_initialization_creates_foundation_tables(test_settings) -> None:
    engine = create_database_engine(test_settings.database_url)
    try:
        Base.metadata.create_all(engine)
        assert FOUNDATION_TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_sqlite_enforces_foreign_keys(test_settings) -> None:
    engine = create_database_engine(test_settings.database_url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()


def test_foundational_records_and_relationships_can_be_saved(test_settings) -> None:
    engine = create_database_engine(test_settings.database_url)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            user = UserAccount(email="renter@example.test")
            user.profile = UserProfile(given_name="Amina", preferred_name="Mina")
            role = Role(code="renter", name="Renter")
            permission = Permission(code="profile:read", description="Read own profile")
            user.role_assignments.append(UserRoleAssignment(role=role))
            role.permission_assignments.append(RolePermission(permission=permission))
            setting = ApplicationSetting(key="support.hours", value={"timezone": "Africa/Nairobi"})
            audit = AuditEvent(
                event_type="phase2.test", actor=user, metadata_json={"source": "test"}
            )
            notification = InAppNotification(
                recipient=user,
                category="system",
                title="Welcome",
                body="Account setup can be added in a future phase.",
            )
            session.add_all([user, role, permission, setting, audit, notification])
            session.commit()

            assert user.id is not None
            assert user.profile is not None and user.profile.given_name == "Amina"
            assert user.role_assignments[0].role.code == "renter"
            assert role.permission_assignments[0].permission.code == "profile:read"
            assert audit.id is not None and notification.id is not None
    finally:
        engine.dispose()


def test_account_contact_constraint_is_enforced(test_settings) -> None:
    engine = create_database_engine(test_settings.database_url)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(UserAccount())
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
            else:
                raise AssertionError("Account with no contact method was accepted.")
    finally:
        engine.dispose()
