from admin.config import Config


def test_dashboard(dashboard_get_mock, client):
    response = client.get(f"{Config.APPLICATION_ROOT}/")
    assert response.status_code == 200
    response_text = response.text
    assert dashboard_get_mock.get("latest_collected") in response_text


def test_users(users_get_mock, client):
    response = client.get(f"{Config.APPLICATION_ROOT}/users")
    assert response.status_code == 200
    response_text = response.text
    assert users_get_mock[0].get("username") in response_text
