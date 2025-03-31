from flask import url_for


def test_users_form_get(users_get_mock, organizations_get_mock, roles_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_user", user_id=0), headers=htmx_header)
    assert response.status_code == 200
    data = form_data(response.text)
    assert set(data.keys()) == {"username", "name", "password", "roles[]", "organization"}


def test_users_form_put(users_put_mock, authenticated_client, htmx_header):
    user = {
        "name": "Test User",
        "organization": 1,
        "roles[]": [1],
        "username": "test",
    }
    response = authenticated_client.put(url_for("admin.edit_user", user_id=1), headers=htmx_header, data=user)
    assert response.status_code == 200
    assert response.headers.get("HX-Refresh") == "true"


def test_users_form_delete(users_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_user", user_id=2), headers=htmx_header)
    assert response.status_code == 200
    assert response.headers.get("HX-Refresh") == "true"
