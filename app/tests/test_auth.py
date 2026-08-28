def test_register_and_login(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Tenant",
            "email": "jane@test.com",
            "password": "password123",
            "role": "tenant",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "jane@test.com"

    resp = client.post(
        "/api/v1/auth/login", json={"email": "jane@test.com", "password": "password123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Bob",
            "email": "bob@test.com",
            "password": "correctpass",
            "role": "tenant",
        },
    )
    resp = client.post(
        "/api/v1/auth/login", json={"email": "bob@test.com", "password": "wrongpass"}
    )
    assert resp.status_code == 401


def test_duplicate_registration_fails(client):
    payload = {
        "full_name": "Dup",
        "email": "dup@test.com",
        "password": "password123",
        "role": "tenant",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_token(client, admin_headers):
    resp = client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "super_admin"


def test_refresh_token_flow(client):
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ref", "email": "ref@test.com", "password": "password123", "role": "tenant"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "ref@test.com", "password": "password123"})
    refresh_token = login.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_change_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Chg", "email": "chg@test.com", "password": "oldpassword", "role": "tenant"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "chg@test.com", "password": "oldpassword"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = client.put(
        "/api/v1/auth/change-password",
        json={"old_password": "oldpassword", "new_password": "newpassword"},
        headers=headers,
    )
    assert resp.status_code == 200
    # old password should no longer work
    bad = client.post("/api/v1/auth/login", json={"email": "chg@test.com", "password": "oldpassword"})
    assert bad.status_code == 401
    good = client.post("/api/v1/auth/login", json={"email": "chg@test.com", "password": "newpassword"})
    assert good.status_code == 200
