from app.models.users import User


def test_setup_creates_admin(client, db_session, admin_setup_payload):
    r = client.post("/setup", json=admin_setup_payload)
    assert r.status_code == 201
    assert r.json()["message"] == "User created"

    user = db_session.query(User).filter(User.username == "admin").first()
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True


def test_setup__when_admin_exists(client, admin_setup_payload):
    client.post("/setup", json=admin_setup_payload)
    r = client.post("/setup", json=admin_setup_payload)
    assert r.status_code == 409
