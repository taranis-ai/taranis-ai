from flask import url_for


def test_dashboard(dashboard_get_mock, authenticated_client):
    response = authenticated_client.get(url_for("admin.dashboard"))
    assert response.status_code == 200
    response_text = response.text
    assert dashboard_get_mock.get("items")[0].get("latest_collected") in response_text


def test_users(users_get_mock, authenticated_client):
    response = authenticated_client.get(url_for("admin.users"))
    assert response.status_code == 200
    response_text = response.text
    assert users_get_mock.get("items")[0].get("name") in response_text
