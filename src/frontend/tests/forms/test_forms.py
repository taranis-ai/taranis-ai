from flask import url_for


def test_users_form(users_get_mock, organizations_get_mock, roles_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_user", user_id=0), headers=htmx_header)
    assert response.status_code == 200
    data = form_data(response.text)
    assert set(data.keys()) == {"username", "name", "password", "roles[]", "organization"}
