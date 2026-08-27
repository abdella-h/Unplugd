def test_refresh(client, admin_setup_payload, admin_login_credentials):
    client.post("/setup", json=admin_setup_payload)

    login = client.post("/login", json=admin_login_credentials)
    refresh_cookie = login.cookies.get("refresh_token")
    assert refresh_cookie is not None

    r = client.post("/refresh", cookies={"refresh_token": refresh_cookie})

    assert r.status_code == 201

    body = r.json()

    assert "access_token" in body
