def test_login(client, db_session, admin_setup_payload, admin_login_credentials):

    r = client.post("/setup", json=admin_setup_payload)

    r = client.post("/login", json=admin_login_credentials)
    assert r.status_code == 200

    body = r.json()

    assert "access_token" in body
    assert body["token_type"] == "Bearer"
