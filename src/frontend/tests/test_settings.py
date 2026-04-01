def test_flask_cookie_name(app):
    with app.app_context():
        secret_key = app.config.get("JWT_ACCESS_COOKIE_NAME", None)
        assert secret_key == "access_token_cookie"


def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY", None)
        assert secret_key == "test_key_for_tests_only_do_not_use"


def test_settings_export_error_returns_oob_notification(app, monkeypatch):
    from frontend.views.admin_views import settings_views

    class FakeResponse:
        ok = False
        content = b'{"error": "Failed to export stories."}'
        status_code = 500

        @staticmethod
        def json():
            return {"error": "Failed to export stories."}

    class FakeCoreApi:
        def api_download(self, action_url):
            assert action_url == "/admin/export-stories"
            return FakeResponse()

    monkeypatch.setattr(settings_views, "CoreApi", FakeCoreApi)

    with app.test_request_context("/admin/settings/api/admin/export-stories"):
        body, status = settings_views.SettingsView.settings_action("/admin/export-stories")

    assert status == 200
    assert 'hx-swap-oob="true"' in body
    assert '<span id="notification-message">Failed to export stories.</span>' in body
    assert "&lt;section id=&quot;notification-bar&quot;" not in body
