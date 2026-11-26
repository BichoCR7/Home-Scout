"""Operator-only bootstrap commands. Never accept passwords as command arguments."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import create_database_engine, create_session_factory
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.user import UserAccount, UserProfile
from app.services.passwords import password_service


def create_super_admin(email: str) -> None:
    try:
        normalized_email = TypeAdapter(EmailStr).validate_python(email).lower()
    except ValidationError as exc:
        raise SystemExit("Enter a valid administrator email address.") from exc

    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            if session.scalar(
                select(func.count())
                .select_from(UserRoleAssignment)
                .join(Role, Role.id == UserRoleAssignment.role_id)
                .where(Role.code == "super_admin")
            ):
                raise SystemExit("A Super Admin already exists; use audited role management.")
            if session.scalar(select(UserAccount.id).where(UserAccount.email == normalized_email)):
                raise SystemExit("An account with that email already exists.")
            role = session.scalar(select(Role).where(Role.code == "super_admin"))
            if role is None:
                raise SystemExit(
                    "Run the database migrations before creating the first Super Admin."
                )

        password = getpass("New password (12+ characters): ")
        confirmation = getpass("Confirm password: ")
        if not 12 <= len(password) <= 128:
            raise SystemExit("Password must be between 12 and 128 characters.")
        if password != confirmation:
            raise SystemExit("Passwords did not match.")

        with factory.begin() as session:
            if session.scalar(
                select(UserRoleAssignment.user_id)
                .join(Role, Role.id == UserRoleAssignment.role_id)
                .where(Role.code == "super_admin")
                .limit(1)
            ):
                raise SystemExit("A Super Admin was created by another operator. No account added.")
            role = session.scalar(select(Role).where(Role.code == "super_admin").with_for_update())
            if role is None:
                raise SystemExit(
                    "Run the database migrations before creating the first Super Admin."
                )
            now = datetime.now(UTC)
            user = UserAccount(
                email=normalized_email,
                password_hash=password_service.hash(password),
                email_verified_at=now,
                status="active",
            )
            user.profile = UserProfile()
            user.role_assignments.append(
                UserRoleAssignment(role=role, scope_type="global", scope_id="*")
            )
            session.add(user)
            session.flush()
            session.add(
                AuditEvent(
                    event_type="authorization.super_admin_bootstrapped",
                    actor_user_id=user.id,
                    subject_type="user",
                    subject_id=str(user.id),
                )
            )
        print(f"HomeScout Super Admin created for {normalized_email}.")
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="homescout")
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser(
        "create-super-admin", help="Create the first audited platform administrator."
    )
    bootstrap.add_argument("--email", required=True)
    arguments = parser.parse_args()
    if arguments.command == "create-super-admin":
        create_super_admin(arguments.email)


if __name__ == "__main__":
    main()
