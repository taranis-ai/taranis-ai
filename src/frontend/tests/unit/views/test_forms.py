import json
from io import BytesIO
from urllib.parse import urlparse

from flask import url_for
from lxml import html

from frontend.config import Config


def _json_request_body(call):
    body = call.request.body
    if isinstance(body, bytes):
        body = body.decode()
    return json.loads(body or "{}")


def _uploaded_users_file() -> BytesIO:
    content = json.dumps({"version": 1, "data": [{"username": "external-user", "name": "External User"}]}).encode()
    uploaded = BytesIO(content)
    uploaded.name = "users_export.json"
    return uploaded


def _posted_to_users_import(responses_mock) -> bool:
    return any(urlparse(call.request.url).path.endswith("/config/users-import") for call in responses_mock.calls)


def test_users_form_get(users_get_mock, organizations_get_mock, roles_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_user", user_id="0"), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {"username", "name", "password", "roles[]", "organization"}


def test_users_form_put(users_get_mock, users_put_mock, authenticated_client, htmx_header):
    user = {
        "name": "Test User",
        "organization": "organization-1",
        "roles[]": ["role-1"],
        "username": "test",
    }
    response = authenticated_client.post(url_for("admin.edit_user", user_id="user-1"), data=user)
    assert response.status_code == 302
    assert response.headers["Location"] == url_for("admin.users")


def test_users_form_delete(users_delete_mock, users_get_mock, organizations_get_mock, roles_get_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_user", user_id="user-2"), headers=htmx_header)

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert len(notification_span) > 0
    assert response.status_code == 200
    assert users_delete_mock.get("message") in notification_span[0].text_content()


def test_users_import_form_routes_errors_to_notification_bar(organizations_get_mock, roles_get_mock, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.import_users"), headers=htmx_header)

    tree = html.fromstring(response.text)
    form = tree.xpath('//form[@id="form"]')[0]
    table_headers = [header.text_content().strip() for header in tree.xpath("//table/thead/tr/th")]
    assert response.status_code == 200
    assert form.get("hx-target-error") == "#notification-bar"
    assert "Roles to assign" in response.text
    assert table_headers == ["Select", "Role", "Description"]


def test_users_import_success_redirects_without_rendering_nested_form(
    organizations_get_mock,
    roles_get_mock,
    authenticated_client,
    htmx_header,
    responses_mock,
):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/config/users-import",
        json={
            "users": [],
            "count": 0,
            "skipped_users": [{"username": "external-user"}],
            "skipped_count": 1,
            "message": "No users imported; skipped 1 existing user(s)",
        },
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (_uploaded_users_file(), "users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == url_for("admin.users")
    assert "Select JSON File" not in response.get_data(as_text=True)
    with authenticated_client.session_transaction() as session:
        assert session["_flashes"] == [("warning", "No users imported; skipped 1 existing user(s)")]

    post_call = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/config/users-import"))
    assert _json_request_body(post_call) == [
        {
            "username": "external-user",
            "name": "External User",
            "organization": "organization-1",
            "roles": ["role-2"],
        }
    ]


def test_users_import_core_error_renders_notification_without_nested_form(
    organizations_get_mock,
    roles_get_mock,
    authenticated_client,
    htmx_header,
    responses_mock,
):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/config/users-import",
        json={"error": "Invalid data format"},
        status=400,
        content_type="application/json",
    )

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (_uploaded_users_file(), "users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert response.status_code == 400
    assert notification_span
    assert "Invalid data format" in notification_span[0].text_content()
    assert "Select JSON File" not in response.get_data(as_text=True)


def test_users_import_invalid_json_renders_notification_without_traceback(authenticated_client, htmx_header, responses_mock):
    invalid_file = BytesIO(b'{"version": 1, "data": []} broken')

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (invalid_file, "broken_users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert response.status_code == 400
    assert notification_span
    assert "Invalid JSON file" in notification_span[0].text_content()
    assert "Traceback" not in response.get_data(as_text=True)
    assert "Select JSON File" not in response.get_data(as_text=True)
    assert not _posted_to_users_import(responses_mock)


def test_users_import_undecodable_file_renders_notification_without_traceback(authenticated_client, htmx_header, responses_mock):
    invalid_file = BytesIO(b"\xff\xfe\x00")

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (invalid_file, "undecodable_users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert response.status_code == 400
    assert notification_span
    assert "Invalid JSON file" in notification_span[0].text_content()
    assert "Traceback" not in response.get_data(as_text=True)
    assert "Select JSON File" not in response.get_data(as_text=True)
    assert not _posted_to_users_import(responses_mock)


def test_users_import_invalid_export_shape_renders_notification(authenticated_client, htmx_header, responses_mock):
    invalid_file = BytesIO(json.dumps({"version": 1, "users": []}).encode())

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (invalid_file, "invalid_users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert response.status_code == 400
    assert notification_span
    assert "Invalid user import file format" in notification_span[0].text_content()
    assert "Select JSON File" not in response.get_data(as_text=True)
    assert not _posted_to_users_import(responses_mock)


def test_users_import_invalid_export_version_renders_notification(authenticated_client, htmx_header, responses_mock):
    invalid_file = BytesIO(json.dumps({"version": 2, "data": []}).encode())

    response = authenticated_client.post(
        url_for("admin.import_users"),
        data={
            "file": (invalid_file, "unsupported_users_export.json"),
            "organization": "organization-1",
            "roles[]": ["role-2"],
        },
        content_type="multipart/form-data",
        headers=htmx_header,
    )

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert response.status_code == 400
    assert notification_span
    assert "Invalid user import file format" in notification_span[0].text_content()
    assert "Select JSON File" not in response.get_data(as_text=True)
    assert not _posted_to_users_import(responses_mock)


def test_organizations_form_get(organizations_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_organization", organization_id="0"), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {
        "name",
        "description",
        "address[street]",
        "address[city]",
        "address[zip]",
        "address[country]",
    }


def test_organizations_form_put(organizations_get_mock, organizations_put_mock, authenticated_client, htmx_header):
    org = {
        "name": "Test Org",
        "description": "Test Description",
        "address[street]": "Test Street",
        "address[city]": "Test City",
        "address[zip]": "12345",
        "address[country]": "Test Country",
    }
    response = authenticated_client.post(url_for("admin.edit_organization", organization_id="organization-1"), data=org)
    assert response.status_code == 302
    assert response.headers["Location"] == url_for("admin.organizations")


def test_organizations_form_delete(organizations_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_organization", organization_id="organization-2"), headers=htmx_header)

    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert len(notification_span) > 0
    assert response.status_code == 200
    assert organizations_delete_mock.get("message") in notification_span[0].text_content()


def test_roles_form_get(roles_get_mock, permissions_get_mock, form_data, authenticated_client, htmx_header):
    response = authenticated_client.get(url_for("admin.edit_role", role_id="0"), headers=htmx_header)
    assert response.status_code == 200
    assert form_data(response.text).get_cleaned_keys() == {"name", "description", "permissions[]", "tlp_level"}


def test_roles_form_put(roles_put_mock, roles_get_mock, authenticated_client, htmx_header):
    role = {"name": "Test Role", "description": "Test Description", "permissions[]": ["ASSESS_ACCESS"], "tlp_level": "clear"}
    response = authenticated_client.post(url_for("admin.edit_role", role_id="role-1"), data=role)
    assert response.status_code == 302
    assert response.headers["Location"] == url_for("admin.roles")


def test_roles_form_delete(roles_delete_mock, authenticated_client, htmx_header):
    response = authenticated_client.delete(url_for("admin.edit_role", role_id="role-2"), headers=htmx_header)
    tree = html.fromstring(response.text)
    notification_span = tree.xpath('//span[@id="notification-message"]')
    assert len(notification_span) > 0
    assert response.status_code == 200
    assert roles_delete_mock.get("message") in notification_span[0].text_content()
