from flask import url_for


def test_users_form_get(users_get_mock, organizations_get_mock, roles_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_user", user_id=0), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {"username", "name", "password", "roles[]", "organization"}


def test_users_form_put(users_put_mock, authenticated_client, htmx_header):
    user = {
        "name": "Test User",
        "organization": 1,
        "roles[]": [1],
        "username": "test",
    }
    response = authenticated_client.put(url_for("admin.edit_user", user_id=1), headers=htmx_header, data=user)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == url_for("admin.users")


def test_users_form_delete(users_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_user", user_id=2), headers=htmx_header)
    assert response.status_code == 200
    assert response.headers.get("HX-Refresh") == "true"


def test_organizations_form_get(organizations_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_organization", organization_id=0), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {
        "name",
        "description",
        "address[street]",
        "address[city]",
        "address[zip]",
        "address[country]",
    }


def test_organizations_form_put(organizations_put_mock, authenticated_client, htmx_header):
    org = {
        "name": "Test Org",
        "description": "Test Description",
        "address[street]": "Test Street",
        "address[city]": "Test City",
        "address[zip]": "12345",
        "address[country]": "Test Country",
    }
    response = authenticated_client.put(url_for("admin.edit_organization", organization_id=1), headers=htmx_header, data=org)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == url_for("admin.organizations")


def test_organizations_form_delete(organizations_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_organization", organization_id=2), headers=htmx_header)
    assert response.status_code == 200
    assert response.headers.get("HX-Refresh") == "true"


def test_roles_form_get(roles_get_mock, permissions_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_role", role_id=0), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {"name", "description", "permissions[]", "tlp_level"}


def test_roles_form_put(roles_put_mock, authenticated_client, htmx_header):
    role = {"name": "Test Role", "description": "Test Description", "permissions[]": [1], "tlp_level": "clear"}
    response = authenticated_client.put(url_for("admin.edit_role", role_id=1), headers=htmx_header, data=role)
    assert response.status_code == 200
    assert response.headers.get("HX-Redirect") == url_for("admin.roles")


def test_roles_form_delete(roles_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_role", role_id=2), headers=htmx_header)
    assert response.status_code == 200
    assert response.headers.get("HX-Refresh") == "true"
