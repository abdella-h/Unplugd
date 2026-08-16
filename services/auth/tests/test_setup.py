from app.models.users import User


def test_setup_no_admin(client):
    r = client.get("/setup")
    assert r.status_code == 200
    assert r.json()["admin_exists"] is False


def test_setup_with_admin(client, db_session):
    db_session.add(User(
        username="admin",
        email="admin@x.com",
        hashed_password="x",
        role="admin",
    ))
    db_session.commit()

    r = client.get("/setup")
    assert r.status_code == 200
    assert r.json()["admin_exists"] is True
