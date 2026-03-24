from flask import url_for

from frontend.config import Config


def test_non_admin_attributes_page_surfaces_core_forbidden(app, authenticated_client_basic, dashboard_get_mock, responses_mock):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/config/attributes", json={"error": "forbidden"}, status=403)

    with app.test_request_context():
        response = authenticated_client_basic.get(url_for("admin.attributes"))

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'data-testid="attribute-table"' in html
    assert 'data-testid="new-attribute-button"' in html
    assert 'data-testid="admin-menu-Attribute"' in html
    assert "No data available" in html
    assert "Failed to fetch Attribute from: /config/attributes" in html
    assert "Attachment Attachment" not in html
