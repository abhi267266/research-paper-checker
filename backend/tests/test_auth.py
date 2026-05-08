"""TDD: Auth endpoint tests — written before implementation."""

def test_register_success(client):
    resp = client.post("/auth/register", json={"email": "a@b.com", "password": "Password1!"})
    assert resp.status_code == 201
    assert resp.json()["message"] == "User registered successfully"


def test_register_duplicate_email(client):
    payload = {"email": "dup@b.com", "password": "Password1!"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_invalid_password_too_short(client):
    resp = client.post("/auth/register", json={"email": "x@b.com", "password": "abc"})
    assert resp.status_code == 422


def test_login_success(client, registered_user):
    resp = client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    # httpOnly cookies should be set
    assert "humanizer_access_token" in resp.cookies
    assert "humanizer_refresh_token" in resp.cookies


def test_login_wrong_password(client, registered_user):
    resp = client.post("/auth/login", json={"email": registered_user["email"], "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/auth/login", json={"email": "nobody@b.com", "password": "Password1!"})
    assert resp.status_code == 401


def test_refresh_token_rotation(client, registered_user):
    login = client.post("/auth/login", json=registered_user)
    assert login.status_code == 200
    old_access = login.cookies["humanizer_access_token"]

    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.cookies["humanizer_access_token"] != old_access


def test_logout_invalidates_refresh_token(client, registered_user):
    client.post("/auth/login", json=registered_user)
    client.post("/auth/logout")

    # Refresh after logout should fail
    resp = client.post("/auth/refresh")
    assert resp.status_code == 401
