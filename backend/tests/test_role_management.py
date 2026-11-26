"""Audited role management and anti-escalation API rules."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.access_control import Role, UserRoleAssignment
from app.models.audit import AuditEvent
from app.models.user import UserAccount
from app.services.passwords import password_service
from tests.test_authentication import login, register_and_verify


def create_super_admin(client) -> tuple[str, str]:
    email = "root@example.com"
    password = "super-admin-secure-passphrase"
    factory = client.app.state.session_factory
    with factory() as session:
        role = session.scalar(select(Role).where(Role.code == "super_admin"))
        account = UserAccount(
            email=email,
            password_hash=password_service.hash(password),
            email_verified_at=datetime.now(UTC),
            status="active",
        )
        account.role_assignments.append(
            UserRoleAssignment(role=role, scope_type="global", scope_id="*")
        )
        session.add(account)
        session.commit()
    return email, password


def test_super_admin_can_assign_roles_but_cannot_self_escalate(client) -> None:
    register_and_verify(client, "target@example.com")
    admin_email, admin_password = create_super_admin(client)
    admin = login(client, admin_email, admin_password)
    target = client.get(
        "/api/v1/admin/users?q=target%40example.com",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
    )
    assert target.status_code == 200
    target_user = target.json()["items"][0]

    assigned = client.post(
        f"/api/v1/admin/users/{target_user['id']}/roles",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
        json={
            "role_code": "property_manager",
            "scope_type": "portfolio",
            "scope_id": "portfolio-123",
            "current_password": admin_password,
        },
    )
    assert assigned.status_code == 201
    assert assigned.json()["scope_id"] == "portfolio-123"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin['access_token']}"})
    self_escalation = client.post(
        f"/api/v1/admin/users/{me.json()['id']}/roles",
        headers={"Authorization": f"Bearer {admin['access_token']}"},
        json={
            "role_code": "super_admin",
            "scope_type": "global",
            "scope_id": "*",
            "current_password": admin_password,
        },
    )
    assert self_escalation.status_code == 403
    assert self_escalation.json()["error"]["code"] == "self_role_change_forbidden"

    factory = client.app.state.session_factory
    with factory() as session:
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.event_type == "authorization.role_assigned")
        ).all()
        assert len(events) == 1
        assert events[0].metadata_json == {
            "role_code": "property_manager",
            "scope_type": "portfolio",
        }


def test_regular_user_cannot_read_role_administration(client) -> None:
    register_and_verify(client, "ordinary@example.com")
    ordinary = login(client, "ordinary@example.com")
    response = client.get(
        "/api/v1/admin/roles",
        headers={"Authorization": f"Bearer {ordinary['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"
