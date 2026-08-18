from app.models.users import User

ADMIN_PAYLOAD = {
    "first_name": "Adamin",
    "last_name": "Admin",
    "username": "admin",
    "email": "admin@gmail.com",
    "password": "secret",
}


def test_setup_creates_admin(client, db_session):
    r = client.post("/setup", json=ADMIN_PAYLOAD)
    assert r.status_code == 201
    assert r.json()["message"] == "User created"

    user = db_session.query(User).filter(User.username == "admin").first()
    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True


def test_setup__when_admin_exists(client):
    client.post("/setup", json=ADMIN_PAYLOAD)
    r = client.post("/setup", json=ADMIN_PAYLOAD)
    assert r.status_code == 409
