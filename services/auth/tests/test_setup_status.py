from app.models.users import User


def test_setup_status_no_admin(client):
    r = client.get("/setup/status")
    assert r.json()["needs_setup"] is True


def test_setup_status_with_admin(client, db_session):
    db_session.add(
        User(
            username="admin",
            email="admin@x.com",
            hashed_password="x",
            role="admin",
            is_active=True,
        )
    )
    db_session.commit()

    r = client.get("/setup/status")
    assert r.json()["needs_setup"] is False


def test_setup_status_with_disabled_admin(client, db_session):
    db_session.add(
        User(
            username="admin",
            email="admin@x.com",
            hashed_password="x",
            role="admin",
            is_active=False,
        )
    )
    db_session.commit()

    r = client.get("/setup/status")
    assert r.json()["needs_setup"] is True
