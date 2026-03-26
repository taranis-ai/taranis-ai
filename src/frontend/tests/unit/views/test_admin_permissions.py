from flask import url_for


def test_non_admin_attributes_page_is_forbidden(app, authenticated_client_basic):
    with app.test_request_context():
        response = authenticated_client_basic.get(url_for("admin.attributes"))

    assert response.status_code == 403

    html = response.get_data(as_text=True)
    assert "403" in html
    assert "access denied" in html.lower()
