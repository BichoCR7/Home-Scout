"""Public identity endpoints, session lifecycle, and abuse controls."""


def register_and_verify(client, email: str, *, role: str = "tenant") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "a-secure-passphrase-2026",
            "given_name": "Amani",
            "family_name": "Njeri",
            "requested_role_code": role,
        },
    )
    assert response.status_code == 202
    token = response.json()["development_token"]
    assert token
    verified = client.post("/api/v1/auth/email/verify", json={"token": token})
    assert verified.status_code == 200
    return token


def login(client, email: str, password: str = "a-secure-passphrase-2026") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def test_registration_verification_login_refresh_and_logout(client) -> None:
    register_and_verify(client, "tenant@example.com", role="landlord")
    pair = login(client, "tenant@example.com")

    profile = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {pair['access_token']}"}
    )
    assert profile.status_code == 200
    data = profile.json()
    assert data["email"] == "tenant@example.com"
    assert data["roles"] == ["tenant"]
    assert data["profile"]["requested_role_code"] == "landlord"
    assert "password_hash" not in data

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert refreshed.status_code == 200
    new_pair = refreshed.json()
    assert new_pair["refresh_token"] != pair["refresh_token"]
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert replay.status_code == 401

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": new_pair["refresh_token"]})
    assert logout.status_code == 204
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_pair['access_token']}"},
        ).status_code
        == 401
    )


def test_registration_only_allows_low_privilege_self_selection(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "self-admin@example.com",
            "password": "a-secure-passphrase-2026",
            "given_name": "Test",
            "requested_role_code": "super_admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "super_admin" not in response.text


def test_password_reset_is_generic_single_use_and_revokes_sessions(client) -> None:
    register_and_verify(client, "reset@example.com")
    pair = login(client, "reset@example.com")

    request = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "reset@example.com"}
    )
    assert request.status_code == 202
    reset_token = request.json()["development_token"]
    assert reset_token
    change = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "another-secure-passphrase-2026"},
    )
    assert change.status_code == 200

    old_access = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {pair['access_token']}"}
    )
    assert old_access.status_code == 401
    replay = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "third-secure-passphrase-2026"},
    )
    assert replay.status_code == 400
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "reset@example.com", "password": "a-secure-passphrase-2026"},
        ).status_code
        == 401
    )
    assert login(client, "reset@example.com", "another-secure-passphrase-2026")["access_token"]


def test_login_errors_are_generic_and_throttled(client) -> None:
    for _ in range(8):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"
        assert "missing@example.com" not in response.text
        assert "wrong-password" not in response.text

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    assert limited.status_code == 429


def test_sessions_are_private_and_revocable(client) -> None:
    register_and_verify(client, "first@example.com")
    register_and_verify(client, "second@example.com")
    first = login(client, "first@example.com")
    second = login(client, "second@example.com")

    first_sessions = client.get(
        "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {first['access_token']}"}
    )
    assert first_sessions.status_code == 200
    assert len(first_sessions.json()) == 1
    first_session_id = first_sessions.json()[0]["id"]
    second_session_id = client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {second['access_token']}"},
    ).json()[0]["id"]
    forbidden = client.delete(
        f"/api/v1/auth/sessions/{second_session_id}",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    assert forbidden.status_code == 404
    revoked = client.delete(
        f"/api/v1/auth/sessions/{first_session_id}",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    assert revoked.status_code == 204
    invalidated = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {first['access_token']}"}
    )
    assert invalidated.status_code == 401
