from datetime import datetime, timezone

import jwt

from app.core.security import ALGORITHM, SECRET_KEY
from app.models.users import User


def test_login(client, db_session, admin_setup_payload, admin_login_credentials):

    r = client.post("/setup", json=admin_setup_payload)

    r = client.post("/login", json=admin_login_credentials)
    assert r.status_code == 200

    body = r.json()

    assert "access_token" in body
    assert body["token_type"] == "Bearer"

    assert "refresh_token" in r.cookies


def test_login_wrong_password(client, admin_setup_payload):
    client.post("/setup", json=admin_setup_payload)

    r = client.post("/login", json={"username": "admin", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"


def test_login_unknown_user(client):
    r = client.post("/login", json={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"


def test_login_disabled_user(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    client.post("/setup", json=admin_setup_payload)

    user = db_session.query(User).filter(User.username == "admin").first()
    user.is_active = False
    db_session.commit()

    r = client.post("/login", json=admin_login_credentials)
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid username or password"
    assert "access_token" not in r.json()


def test_login_access_token_claims(
    client, admin_setup_payload, admin_login_credentials
):
    client.post("/setup", json=admin_setup_payload)

    r = client.post("/login", json=admin_login_credentials)
    assert r.status_code == 200

    token = r.json()["access_token"]

    header = jwt.get_unverified_header(token)
    assert header["alg"] == ALGORITHM == "HS256"

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload

    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = (exp - now).total_seconds()
    assert 14 * 60 <= delta <= 16 * 60
