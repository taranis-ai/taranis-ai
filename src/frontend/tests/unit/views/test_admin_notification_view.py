import json

from flask import url_for
from lxml import html

from frontend.config import Config


def _json_request_body(call):
    body = call.request.body
    if isinstance(body, bytes):
        body = body.decode()
    return json.loads(body or "{}")


def test_admin_notifications_page_shows_sidebar_link_form_and_connected_clients(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/realtime/clients",
        json={
            "num_clients": 2,
            "num_users": 1,
            "clients": [
                {"username": "admin", "user_id": "user-1", "client_id": "client-1"},
                {"username": "admin", "user_id": "user-1", "client_id": "client-2"},
            ],
        },
    )

    notifications_url = url_for("admin.notifications")
    response = authenticated_client.get(notifications_url)

    assert response.status_code == 200
    tree = html.fromstring(response.get_data(as_text=True))
    assert tree.xpath(f'//a[@data-testid="admin-menu-Notifications"][@href="{notifications_url}"]')
    form = tree.xpath(f'//form[@hx-post="{notifications_url}"]')[0]
    assert form.get("hx-target") == "#notification-bar"
    assert form.get("hx-target-error") == "#notification-bar"
    assert form.xpath('.//input[@name="message"][@maxlength="500"][@required]')
    assert tree.xpath('//*[@data-testid="connected-client-count"][normalize-space()="2"]')
    assert tree.xpath('//*[@data-testid="connected-user-count"][normalize-space()="1"]')
    assert "client-1" in response.get_data(as_text=True)
    assert "admin" in response.get_data(as_text=True)


def test_admin_broadcast_forwards_exact_message(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/realtime/broadcast",
        json={"message": "Broadcast sent"},
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.post(
        url_for("admin.notifications"),
        data={"message": "  Maintenance at 18:00  "},
    )

    assert response.status_code == 200
    assert "Broadcast sent" in response.get_data(as_text=True)
    post_call = next(call for call in responses_mock.calls if call.request.method == "POST")
    assert _json_request_body(post_call) == {"message": "  Maintenance at 18:00  "}


def test_non_admin_cannot_open_admin_notifications(authenticated_client_basic):
    response = authenticated_client_basic.get(url_for("admin.notifications"))

    assert response.status_code == 403
