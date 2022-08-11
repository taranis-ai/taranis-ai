def test_is_alive(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": true' in response.data


def test_is_alive_fail(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": false' not in response.data


def test_is_not_authorized(client):
    response = client.get("/api/v1/publishers")
    assert response.status_code == 401


def test_is_authorized(client):
    response = client.get("/api/v1/publishers", headers={"Authorization": "Bearer test_key"})
    print(response.data)
    assert response.status_code == 200


def test_get_publishers(client):
    response = client.get("/api/v1/publishers", headers={"Authorization": "Bearer test_key"})
    response_json = response.json
    from publishers.managers.publishers_manager import publishers

    for i, key in enumerate(publishers):
        assert response_json[i]["type"] == key
    assert response.status_code == 200
