from datetime import datetime, timedelta
from typing import cast
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from flask import render_template


def test_flask_cookie_name(app):
    with app.app_context():
        secret_key = app.config.get("JWT_ACCESS_COOKIE_NAME", None)
        assert secret_key == "access_token_cookie"


def test_flask_secret_key(app):
    with app.app_context():
        secret_key = app.config.get("JWT_SECRET_KEY", None)
        assert secret_key == "test_key_for_tests_only_do_not_use"


def test_jwt_decode_leeway(app):
    with app.app_context():
        assert app.config.get("JWT_DECODE_LEEWAY") == 5


def test_realtime_template_gate_requires_feature_flag_and_access_cookie(app, monkeypatch):
    monkeypatch.setitem(app.config, "REALTIME_ENABLED", True)

    with app.test_request_context("/"):
        anonymous_body = render_template("base.html")
    with app.test_request_context("/", headers={"Cookie": f"{app.config['JWT_ACCESS_COOKIE_NAME']}=signed-token"}):
        authenticated_body = render_template("base.html")

    assert 'data-realtime-enabled="false"' in anonymous_body
    assert 'data-realtime-enabled="true"' in authenticated_body


def test_settings_export_error_returns_oob_notification(app, monkeypatch):
    from frontend.views.admin_views import settings_views

    class FakeResponse:
        ok = False
        content = b'{"error": "Failed to export stories."}'
        status_code = 500
        text = '{"error": "Failed to export stories."}'

        @staticmethod
        def json():
            return {"error": "Failed to export stories."}

    class FakeCoreApi:
        def api_download(self, action_url):
            assert action_url == "/settings/export-stories"
            return FakeResponse()

    monkeypatch.setattr(settings_views, "CoreApi", FakeCoreApi)
    monkeypatch.setattr(
        settings_views.SettingsView,
        "static_view",
        classmethod(lambda cls: ('<div id="settings-container"></div>', 200)),
    )

    with app.test_request_context("/admin/settings/api/settings/export-stories"):
        body, status = cast(tuple[str, int], settings_views.SettingsView.settings_action("/settings/export-stories"))

    assert status == 500
    assert 'hx-swap-oob="true"' in body
    assert '<span id="notification-message">Failed to export stories.</span>' in body
    assert "&lt;section id=&quot;notification-bar&quot;" not in body


def test_story_transfer_partial_guards_future_export_dates(authenticated_client, auth_user, responses):
    from frontend.cache import add_user_to_cache
    from frontend.config import Config

    user = auth_user.model_copy(deep=True)
    user.profile.timezone = "Europe/Vienna"
    add_user_to_cache(user.model_dump(mode="json"))
    responses.get(f"{Config.TARANIS_CORE_URL}/settings/settings", json={"items": [{"settings": {}}]})
    body = authenticated_client.get("/admin/settings/").get_data(as_text=True)

    assert 'data-testid="story-export-time-from"' in body
    assert 'data-testid="story-export-time-to"' in body
    now = datetime.now(ZoneInfo("Europe/Vienna"))
    assert any(body.count(f'max="{minute:%Y-%m-%dT%H:%M}"') == 2 for minute in (now, now - timedelta(minutes=1)))
    assert "profile timezone (Europe/Vienna)" in body
    responses.get(f"{Config.TARANIS_CORE_URL}/settings/export-stories", json=[])
    response = authenticated_client.get("/admin/settings/export-stories?timefrom=2024-01-01T12:00&timeto=2024-07-01T12:00&metadata=true")
    assert response.status_code == 200
    assert parse_qs(urlparse(responses.calls[-1].request.url).query) == {
        "timefrom": ["2024-01-01T11:00:00+00:00"],
        "timeto": ["2024-07-01T10:00:00+00:00"],
        "metadata": ["true"],
    }


def test_settings_patch_action_sends_only_submitted_fields(app, monkeypatch):
    from frontend.views.admin_views import settings_views

    calls = []

    class FakeResponse:
        ok = True
        content = b'{"message": "Successfully updated settings"}'
        status_code = 200

        @staticmethod
        def json():
            return {"message": "Successfully updated settings"}

    class FakeCoreApi:
        def api_patch(self, action_url, json_data=None):
            calls.append((action_url, json_data))
            return FakeResponse()

    monkeypatch.setattr(settings_views, "CoreApi", FakeCoreApi)
    monkeypatch.setattr(
        settings_views.SettingsView,
        "static_view",
        classmethod(lambda cls: ('<div id="settings-container"></div>', 200)),
    )

    with app.test_request_context(
        "/admin/settings/settings",
        method="PATCH",
        data={"settings[default_collector_proxy]": "http://proxy.test", "settings[onboarding_enabled]": "false"},
    ):
        body, status = cast(tuple[str, int], settings_views.SettingsView.settings_action("/settings/settings", method="patch"))

    assert status == 200
    assert calls == [
        (
            "/settings/settings",
            {"settings": {"default_collector_proxy": "http://proxy.test", "onboarding_enabled": False}},
        )
    ]
    assert '<span id="notification-message">Successfully updated settings</span>' in body
