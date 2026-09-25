from datetime import datetime


def _admin_headers(client, setup_payload, login_credentials):
    setup = client.post("/setup", json=setup_payload)
    assert setup.status_code == 201, setup.text

    login = client.post("/login", json=login_credentials)
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_me_returns_current_admin_profile(
    client, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    response = client.get("/me", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_name"] == "Adamin"
    assert body["last_name"] == "Admin"
    assert body["username"] == "admin"
    assert body["email"] == "admin@gmail.com"
    assert body["role"] == "admin"
    assert body["datacenter_id"] is None
    assert body["is_active"] is True
    assert body["last_login_at"] is not None
    assert datetime.fromisoformat(body["last_login_at"]).tzinfo is not None
    assert "id" not in body
    assert "hashed_password" not in body


def test_me_returns_operator_profile(
    client, admin_setup_payload, admin_login_credentials
):
    admin_headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    invite = client.post(
        "/register/operator/invite",
        json={"email": "operator@example.com", "datacenter_id": 7},
        headers=admin_headers,
    )
    assert invite.status_code == 201, invite.text
    invite_token = invite.json()["invite_token"]

    accepted = client.post(
        "/register/operator/accept",
        json={
            "token": invite_token,
            "username": "operator",
            "password": "StrongPass123",
            "first_name": "Op",
            "last_name": "Erator",
        },
    )
    assert accepted.status_code == 200, accepted.text

    operator_login = client.post(
        "/login", json={"username": "operator", "password": "StrongPass123"}
    )
    assert operator_login.status_code == 200, operator_login.text
    operator_headers = {
        "Authorization": f"Bearer {operator_login.json()['access_token']}"
    }

    response = client.get("/me", headers=operator_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_name"] == "Op"
    assert body["last_name"] == "Erator"
    assert body["username"] == "operator"
    assert body["email"] == "operator@example.com"
    assert body["role"] == "operator"
    assert body["datacenter_id"] == 7
    assert body["is_active"] is True
    assert body["last_login_at"] is not None


def test_me_requires_authentication(client):
    response = client.get("/me")

    assert response.status_code == 401, response.text
