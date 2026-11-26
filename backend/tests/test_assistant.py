"""Privacy, provider, ownership, and rate-limit checks for the Phase 13 assistant."""

import base64
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from starlette.testclient import TestClient

from app.models.assistant import AssistantConversation, AssistantMessage, AssistantRateWindow
from app.services.ai_provider import AiProviderUnavailable
from tests.helpers import create_authenticated_user
from tests.test_marketplace import _publish_listing
from tests.test_properties import _create_payload


class StubProvider:
    def __init__(self, answer: str = "Here is a careful answer.", fail: bool = False) -> None:
        self.answer = answer
        self.fail = fail
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def complete(self, instructions: str, messages: list[dict[str, str]]) -> str:
        self.calls.append((instructions, messages))
        if self.fail:
            raise AiProviderUnavailable
        return self.answer


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _enable_assistant(
    client: TestClient, *, limit: int = 10, provider: StubProvider | None = None
) -> StubProvider:
    encryption_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode()
    client.app.state.settings = client.app.state.settings.model_copy(
        update={
            "ai_enabled": True,
            "ai_api_base_url": "https://ai.example.test/v1",
            "ai_model": "homes-test",
            "ai_api_key": SecretStr("test-provider-key"),
            "ai_encryption_key": SecretStr(encryption_key),
            "ai_requests_per_minute": limit,
        }
    )
    stub = provider or StubProvider()
    client.app.state.assistant_client = stub
    return stub


def test_configuration_is_truthful_and_does_not_expose_provider_secrets(client) -> None:
    response = client.get("/api/v1/assistant/configuration")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert "not connected" in body["disabled_message"].lower()
    assert "test-provider-key" not in response.text
    assert "api_key" not in response.text.lower()


def test_sending_requires_current_provider_consent(client) -> None:
    token = create_authenticated_user(
        client, role_code="tenant", email="assistant-consent@example.com"
    )
    provider = _enable_assistant(client)
    response = client.post(
        "/api/v1/assistant/messages",
        headers=_auth(token),
        json={"text": "Find me a home"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "assistant_consent_required"
    assert provider.calls == []


def test_conversation_is_encrypted_owner_scoped_renamable_and_deletable(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="assistant-owner@example.com"
    )
    other = create_authenticated_user(
        client, role_code="tenant", email="assistant-other@example.com"
    )
    provider = _enable_assistant(client)
    headers = _auth(owner)

    accepted = client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["provider_processing_allowed"] is True

    sent = client.post(
        "/api/v1/assistant/messages",
        headers=headers,
        json={"text": "How do I compare two rents?", "intent": "property_cost_explanation"},
    )
    assert sent.status_code == 200, sent.text
    body = sent.json()
    conversation_id = body["conversation"]["id"]
    assert body["assistant_message"]["text"] == provider.answer
    assert len(provider.calls) == 1

    owner_id = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    session = client.app.state.session_factory()
    try:
        row = session.get(AssistantConversation, UUID(conversation_id))
        stored_message = session.scalar(
            select(AssistantMessage).where(
                AssistantMessage.conversation_id == UUID(conversation_id),
                AssistantMessage.role == "user",
            )
        )
        assert row is not None and stored_message is not None
        assert b"How do I compare two rents?" not in stored_message.encrypted_content
        assert b"How do I compare two rents?" not in row.encrypted_title
        assert row.owner_user_id == owner_id
    finally:
        session.close()

    hidden = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}",
        headers=_auth(other),
    )
    assert hidden.status_code == 404

    renamed = client.patch(
        f"/api/v1/assistant/conversations/{conversation_id}",
        headers=headers,
        json={"title": "Rent comparison"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Rent comparison"
    detail = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}",
        headers=headers,
    )
    assert [item["role"] for item in detail.json()["messages"]] == ["user", "assistant"]

    revoked = client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": False},
    )
    assert revoked.status_code == 200
    assert revoked.json()["provider_processing_allowed"] is False
    assert (
        client.delete(
            f"/api/v1/assistant/conversations/{conversation_id}", headers=headers
        ).status_code
        == 204
    )


def test_provider_failure_saves_no_prompt_or_generated_answer(client) -> None:
    token = create_authenticated_user(
        client, role_code="tenant", email="assistant-failure@example.com"
    )
    provider = _enable_assistant(client, provider=StubProvider(fail=True))
    headers = _auth(token)
    client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": True},
    )

    response = client.post(
        "/api/v1/assistant/messages",
        headers=headers,
        json={"text": "Please help me plan a move"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "assistant_provider_unavailable"
    session = client.app.state.session_factory()
    try:
        assert list(session.scalars(select(AssistantConversation))) == []
        assert list(session.scalars(select(AssistantMessage))) == []
        assert (
            session.get(
                AssistantRateWindow,
                UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"]),
            )
            is not None
        )
    finally:
        session.close()
    assert len(provider.calls) == 1


def test_rate_limit_is_account_scoped(client) -> None:
    token = create_authenticated_user(
        client, role_code="tenant", email="assistant-rate@example.com"
    )
    _enable_assistant(client, limit=1)
    headers = _auth(token)
    client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": True},
    )

    first = client.post(
        "/api/v1/assistant/messages", headers=headers, json={"text": "Help me budget"}
    )
    second = client.post(
        "/api/v1/assistant/messages", headers=headers, json={"text": "Help me search"}
    )
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "assistant_rate_limited"


def test_explicit_property_context_uses_only_current_public_listing_records(client) -> None:
    owner = create_authenticated_user(
        client, role_code="landlord", email="assistant-listing-owner@example.com"
    )
    renter = create_authenticated_user(
        client, role_code="tenant", email="assistant-listing-renter@example.com"
    )
    listing = _publish_listing(client, owner, title="Assistant context test home", rent=31_500)
    provider = _enable_assistant(client)
    headers = _auth(renter)
    client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": True},
    )

    response = client.post(
        "/api/v1/assistant/messages",
        headers=headers,
        json={
            "text": "Explain this rent and the listing details",
            "intent": "property_explanation",
            "property_id": listing["id"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["context_properties"][0]["id"] == listing["id"]
    instructions, _messages = provider.calls[0]
    assert "Homes the user explicitly selected" in instructions
    assert "rent=KSh 31500" in instructions
    assert "owner_user_id" not in instructions


def test_shared_context_requires_active_group_membership(client) -> None:
    owner = create_authenticated_user(
        client, role_code="tenant", email="assistant-group-owner@example.com"
    )
    outsider = create_authenticated_user(
        client, role_code="tenant", email="assistant-group-outsider@example.com"
    )
    owner_id = client.get("/api/v1/auth/me", headers=_auth(owner)).json()["id"]
    group = client.post(
        "/api/v1/collaboration/groups",
        headers=_auth(owner),
        json={"name": "Private moving plan", "invite_user_ids": []},
    )
    assert group.status_code == 201, group.text
    provider = _enable_assistant(client)
    headers = _auth(outsider)
    client.put(
        "/api/v1/assistant/privacy",
        headers=headers,
        json={"provider_processing_allowed": True},
    )

    response = client.post(
        "/api/v1/assistant/messages",
        headers=headers,
        json={
            "text": "Help coordinate this search",
            "intent": "shared_house_hunting",
            "shared_group_id": group.json()["id"],
        },
    )
    assert response.status_code == 404
    assert provider.calls == []
    assert owner_id != client.get("/api/v1/auth/me", headers=headers).json()["id"]


def test_role_work_context_includes_only_owned_work_and_keeps_drafts_private(client) -> None:
    owner = create_authenticated_user(
        client, role_code="landlord", email="assistant-work-owner@example.com"
    )
    other = create_authenticated_user(
        client, role_code="landlord", email="assistant-work-other@example.com"
    )
    draft = client.post(
        "/api/v1/properties",
        headers=_auth(owner),
        json=_create_payload(client, title="Owner's private draft"),
    )
    assert draft.status_code == 201, draft.text
    provider = _enable_assistant(client)
    owner_headers = _auth(owner)
    other_headers = _auth(other)
    for headers in (owner_headers, other_headers):
        consent = client.put(
            "/api/v1/assistant/privacy",
            headers=headers,
            json={"provider_processing_allowed": True},
        )
        assert consent.status_code == 200

    own = client.post(
        "/api/v1/assistant/messages",
        headers=owner_headers,
        json={"text": "Help improve my draft listing", "include_work_context": True},
    )
    outsider = client.post(
        "/api/v1/assistant/messages",
        headers=other_headers,
        json={"text": "Help with listing work", "include_work_context": True},
    )
    assert own.status_code == 200
    assert outsider.status_code == 200
    assert own.json()["context_properties"] == []
    assert outsider.json()["context_properties"] == []
    assert "Owner's private draft" in provider.calls[0][0]
    assert "Owner's private draft" not in provider.calls[1][0]
    assert "listing_status=draft" in provider.calls[0][0]
