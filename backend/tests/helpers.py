"""Shared backend API-test helpers."""

from sqlalchemy import select

from app.db.base import utc_now
from app.models.access_control import Role, UserRoleAssignment
from app.models.user import UserAccount
from app.services.passwords import password_service


def create_authenticated_user(client, *, role_code: str, email: str) -> str:
    """Create an already-verified fixture account and return its test access token."""

    password = "HomeScout-Test-Password-734!"
    factory = client.app.state.session_factory
    with factory() as session:
        role = session.scalar(select(Role).where(Role.code == role_code))
        assert role is not None
        user = UserAccount(
            email=email,
            password_hash=password_service.hash(password),
            email_verified_at=utc_now(),
            status="active",
        )
        user.role_assignments.append(UserRoleAssignment(role=role))
        session.add(user)
        session.commit()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
