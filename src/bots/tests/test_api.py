def test_is_alive(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": true' in response.data


def test_is_alive_fail(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": false' not in response.data


def test_is_not_authorized(client):
    response = client.get("/api/v1/bots")
    assert response.status_code == 401


def test_is_authorized(client):
    response = client.get("/api/v1/bots", headers={"Authorization": "Bearer test_key"})
    assert response.status_code == 200


def test_get_bots(client):
    from bots.managers.bots_manager import get_registered_bots_info

    response = client.get("/api/v1/bots", headers={"Authorization": "Bearer test_key"})
    assert response.json == get_registered_bots_info()
    assert response.status_code == 200
