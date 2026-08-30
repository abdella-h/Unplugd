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
