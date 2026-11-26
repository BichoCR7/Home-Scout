"""Default-deny authorization, ownership checks, and scoped assignments."""

from uuid import uuid4

from sqlalchemy import select

from app.core.rbac_catalog import ROLE_PERMISSION_CODES
from app.models.access_control import Role, UserRoleAssignment
from app.models.user import UserAccount
from app.services.authorization import AuthorizationService


def test_roles_do_not_receive_another_role_private_permissions() -> None:
    assert "financial_record:view:self" in ROLE_PERMISSION_CODES["tenant"]
    assert "financial_record:view:self" not in ROLE_PERMISSION_CODES["landlord"]
    assert "financial_record:view:self" not in ROLE_PERMISSION_CODES["admin"]
    assert "payment_record:view:booking_participant" in ROLE_PERMISSION_CODES["service_provider"]


def test_owned_resources_require_matching_owner_and_scoped_role(client) -> None:
    factory = client.app.state.session_factory
    owner_id = uuid4()
    other_id = uuid4()
    property_id = "property-123"
    with factory() as session:
        role = session.scalar(select(Role).where(Role.code == "landlord"))
        user = UserAccount(id=owner_id, email="owner@example.com", status="active")
        user.role_assignments.append(
            UserRoleAssignment(role=role, scope_type="global", scope_id="*")
        )
        session.add(user)
        session.commit()

        service = AuthorizationService()
        assert service.has_permission(
            session,
            user_id=owner_id,
            permission_code="property:view:owned",
            resource_owner_id=owner_id,
            resource_scope_type="property",
            resource_scope_id=property_id,
        )
        assert not service.has_permission(
            session,
            user_id=owner_id,
            permission_code="property:view:owned",
            resource_owner_id=other_id,
            resource_scope_type="property",
            resource_scope_id=property_id,
        )


def test_scoped_assignment_cannot_access_another_scope(client) -> None:
    factory = client.app.state.session_factory
    user_id = uuid4()
    with factory() as session:
        role = session.scalar(select(Role).where(Role.code == "real_estate_agent"))
        user = UserAccount(id=user_id, email="agent@example.com", status="active")
        user.role_assignments.append(
            UserRoleAssignment(
                role=role,
                scope_type="property",
                scope_id="property-123",
            )
        )
        session.add(user)
        session.commit()

        service = AuthorizationService()
        assert service.has_permission(
            session,
            user_id=user_id,
            permission_code="listing:edit:assigned",
            resource_scope_type="property",
            resource_scope_id="property-123",
        )
        assert not service.has_permission(
            session,
            user_id=user_id,
            permission_code="listing:edit:assigned",
            resource_scope_type="property",
            resource_scope_id="property-456",
        )
