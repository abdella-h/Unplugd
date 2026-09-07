import hashlib
from datetime import datetime, timedelta, timezone

from app.models.users import User


def _admin_headers(client, setup_payload, login_creds):
    client.post("/setup", json=setup_payload)
    r = client.post("/login", json=login_creds)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _invite_payload(**overrides):
    payload = {
        "email": "op1@example.com",
        "datacenter_id": 7,
    }
    payload.update(overrides)
    return payload


def _accept_payload(
    token, username="op1", password="StrongPass123", first_name="Op", last_name="One", **overrides
):
    payload = {
        "token": token,
        "username": username,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
    }
    payload.update(overrides)
    return payload


# --- Invite: auth + validation ---


def test_invite_happy_returns_201_with_link(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)

    assert r.status_code == 201, r.text
    body = r.json()
    assert "invite_token" in body
    assert "invite_link" in body
    assert "expires_at" in body
    assert body["invite_token"] in body["invite_link"]


def test_invite_requires_auth(client):
    r = client.post("/register/operator/invite", json=_invite_payload())
    assert r.status_code in (401, 403), r.text


def test_invite_forbids_operator(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    # admin invites one operator, operator accepts, then tries to invite another
    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    token = r.json()["invite_token"]

    r = client.post("/register/operator/accept", json=_accept_payload(token))
    assert r.status_code == 200, r.text

    op_login = client.post(
        "/login", json={"username": "op1", "password": "StrongPass123"}
    )
    assert op_login.status_code == 200, op_login.text
    op_headers = {"Authorization": f"Bearer {op_login.json()['access_token']}"}

    r = client.post(
        "/register/operator/invite",
        json=_invite_payload(email="op2@example.com"),
        headers=op_headers,
    )
    assert r.status_code == 403, r.text


def test_invite_rejects_missing_dc(client, admin_setup_payload, admin_login_credentials):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    payload = _invite_payload()
    del payload["datacenter_id"]
    r = client.post("/register/operator/invite", json=payload, headers=headers)
    assert r.status_code == 422, r.text


def test_invite_rejects_missing_email(
    client, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    payload = _invite_payload()
    del payload["email"]
    r = client.post("/register/operator/invite", json=payload, headers=headers)
    assert r.status_code == 422, r.text


def test_invite_rejects_names(client, admin_setup_payload, admin_login_credentials):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post(
        "/register/operator/invite",
        json=_invite_payload(first_name="Op", last_name="One"),
        headers=headers,
    )
    assert r.status_code == 422, r.text


def test_invite_perdc_admin_pinned(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    client.post("/setup", json=admin_setup_payload)
    admin = db_session.query(User).filter(User.username == "admin").first()
    admin.datacenter_id = 3
    db_session.commit()

    login = client.post("/login", json=admin_login_credentials)
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # other DC -> forbidden
    r = client.post(
        "/register/operator/invite", json=_invite_payload(datacenter_id=7), headers=headers
    )
    assert r.status_code == 403, r.text

    # own DC -> allowed
    r = client.post(
        "/register/operator/invite",
        json=_invite_payload(email="own@example.com", datacenter_id=3),
        headers=headers,
    )
    assert r.status_code == 201, r.text


def test_invite_duplicate_409(client, admin_setup_payload, admin_login_credentials):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 409, r.text


# --- Invite: side effects ---


def test_invite_creates_inactive_operator(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text

    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "op1@example.com").first()
    assert user is not None
    assert user.role == "operator"
    assert user.is_active is False
    assert user.datacenter_id == 7
    # username is a placeholder until the operator picks one at accept
    assert user.username.startswith("pending-")

    # inactive cannot login yet (matches login.py uniform 401)
    r = client.post("/login", json={"username": user.username, "password": "anything"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"


def test_invite_stores_hash_only(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    from app.models.invites import InviteToken

    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    raw = r.json()["invite_token"]

    expected_hash = hashlib.sha256(raw.encode()).hexdigest()
    db_session.expire_all()
    row = (
        db_session.query(InviteToken)
        .filter(InviteToken.token_hash == expected_hash)
        .first()
    )
    assert row is not None
    assert row.used_at is None
    # raw value must never be stored
    assert (
        db_session.query(InviteToken).filter(InviteToken.token_hash == raw).first()
        is None
    )


# --- Accept ---


def test_accept_happy_activates(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    token = r.json()["invite_token"]

    r = client.post("/register/operator/accept", json=_accept_payload(token, username="op1"))
    assert r.status_code == 200, r.text

    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "op1").first()
    assert user is not None
    assert user.email == "op1@example.com"
    assert user.is_active is True
    assert user.first_name == "Op"
    assert user.last_name == "One"

    r = client.post("/login", json={"username": "op1", "password": "StrongPass123"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_accept_rejects_missing_username(
    client, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    token = r.json()["invite_token"]

    r = client.post(
        "/register/operator/accept", json={"token": token, "password": "StrongPass123"}
    )
    assert r.status_code == 422, r.text


def test_accept_duplicate_username_409(
    client, admin_setup_payload, admin_login_credentials
):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    token1 = r.json()["invite_token"]
    r = client.post("/register/operator/accept", json=_accept_payload(token1, username="op1"))
    assert r.status_code == 200, r.text

    r = client.post(
        "/register/operator/invite",
        json=_invite_payload(email="op2@example.com"),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    token2 = r.json()["invite_token"]

    r = client.post("/register/operator/accept", json=_accept_payload(token2, username="op1"))
    assert r.status_code == 409, r.text


def test_accept_replay_410(client, admin_setup_payload, admin_login_credentials):
    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    token = r.json()["invite_token"]

    r = client.post("/register/operator/accept", json=_accept_payload(token, username="op1"))
    assert r.status_code == 200, r.text

    r = client.post(
        "/register/operator/accept",
        json=_accept_payload(token, username="op1-retry", password="AnotherPass123"),
    )
    assert r.status_code == 410, r.text


def test_accept_invalid_404(client):
    r = client.post(
        "/register/operator/accept",
        json=_accept_payload("no-such-token", username="ghost"),
    )
    assert r.status_code == 404, r.text


def test_accept_expired_404(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    from app.models.invites import InviteToken

    headers = _admin_headers(client, admin_setup_payload, admin_login_credentials)

    r = client.post("/register/operator/invite", json=_invite_payload(), headers=headers)
    assert r.status_code == 201, r.text
    raw = r.json()["invite_token"]

    db_session.expire_all()
    row = (
        db_session.query(InviteToken)
        .filter(InviteToken.token_hash == hashlib.sha256(raw.encode()).hexdigest())
        .first()
    )
    assert row is not None
    row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    r = client.post("/register/operator/accept", json=_accept_payload(raw, username="op1"))
    assert r.status_code == 404, r.text
