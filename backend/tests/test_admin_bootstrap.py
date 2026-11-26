"""The first Super Admin bootstrap is operator-only and single-use."""

import pytest
from sqlalchemy import select

import app.cli as cli
from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.user import UserAccount


def test_bootstrap_creates_one_verified_super_admin(client, monkeypatch) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: client.app.state.settings)
    prompts = iter(["bootstrap-passphrase-2026", "bootstrap-passphrase-2026"])
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(prompts))

    cli.create_super_admin("root@example.com")

    factory = client.app.state.session_factory
    with factory() as session:
        account = session.scalar(select(UserAccount).where(UserAccount.email == "root@example.com"))
        role = session.scalar(select(Role).where(Role.code == "super_admin"))
        assignment = session.get(UserRoleAssignment, (account.id, role.id, "global", "*"))
        audit = session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_type == "authorization.super_admin_bootstrapped"
            )
        )
        assert account.status == "active"
        assert account.email_verified_at is not None
        assert account.password_hash != "bootstrap-passphrase-2026"
        assert assignment is not None
        assert audit is not None

    with pytest.raises(SystemExit, match="A Super Admin already exists"):
        cli.create_super_admin("second-root@example.com")
