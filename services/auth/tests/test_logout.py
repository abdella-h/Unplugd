import hashlib

from app.models.refresh_tokens import RefreshToken


def test_logout_success(
    client, db_session, admin_setup_payload, admin_login_credentials
):
    client.post("/setup", json=admin_setup_payload)
    login = client.post("/login", json=admin_login_credentials)
    refresh_cookie = login.cookies.get("refresh_token")
    assert refresh_cookie is not None
    token_hash = hashlib.sha256(refresh_cookie.encode()).hexdigest()
    row_before = (
        db_session.query(RefreshToken)
        .filter(RefreshToken.hashed_token == token_hash)
        .first()
    )
    assert row_before is not None
    assert row_before.revoked_at is None
    r = client.post("/logout", cookies={"refresh_token": refresh_cookie})
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert "refresh_token" in set_cookie.lower()
    assert 'refresh_token=""' in set_cookie
    assert refresh_cookie not in set_cookie
    assert r.cookies.get("refresh_token") in (None, "")
    db_session.expire_all()
    row_after = (
        db_session.query(RefreshToken)
        .filter(RefreshToken.hashed_token == token_hash)
        .first()
    )
    assert row_after is not None
    assert row_after.revoked_at is not None
