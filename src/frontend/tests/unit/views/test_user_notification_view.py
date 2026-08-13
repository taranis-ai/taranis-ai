from flask import url_for


def test_notification_center_renders_without_a_core_request(authenticated_client_basic):
    with authenticated_client_basic.application.app_context():
        url = url_for("user.notifications")

    response = authenticated_client_basic.get(url)

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-testid="notification-center-page"' in body
    assert "data-notification-center-list" in body
    assert 'data-testid="nav-notification-center"' in body
    assert 'src="/static/js/notification-center.js"' in body
