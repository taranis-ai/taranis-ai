def test_is_alive(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": true' in response.data


def test_is_alive_fail(client):
    response = client.get("/api/v1/isalive")
    assert b'"isalive": false' not in response.data


def test_is_not_authorized(client):
    response = client.get("/api/v1/presenters")
    assert response.status_code == 401


def test_is_authorized(client):
    response = client.get("/api/v1/presenters", headers={"Authorization": "Bearer test_key"})
    assert response.status_code == 200


def test_get_presenters(client):
    response = client.get("/api/v1/presenters", headers={"Authorization": "Bearer test_key"})
    # response_json = response.json
    # from presenters.managers.presenters_manager import presenters
    # for i, key in enumerate(presenters):
    #    assert response_json[i]["type"] == key
    assert response.status_code == 200
