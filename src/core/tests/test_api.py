def test_is_alive(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": true' in response.data


def test_is_alive_fail(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": false' not in response.data


def test_auth_login_fail(client):
    response = client.get("/api/v1/auth/login")
    assert response.status_code == 401


def test_auth_logout(client):
    response = client.get("/api/v1/auth/logout")
    assert response.status_code == 200


def test_auth_login(client):
    body = {"username": "admin", "password": "admin"}
    response = client.post("/api/v1/auth/login", json=body)
    assert response.status_code == 200


def test_access_token(access_token):
    assert access_token is not None


def test_user_profile(client, auth_header):
    response = client.get("/api/v1/users/my-profile", headers=auth_header)
    assert response.json
    assert response.data
    assert response.status_code == 200
