from typing import cast

import pytest
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

    assert status == 200
    assert 'hx-swap-oob="true"' in body
    assert '<span id="notification-message">Failed to export stories.</span>' in body
    assert "&lt;section id=&quot;notification-bar&quot;" not in body


def test_story_transfer_partial_guards_future_export_dates(app):
    with app.test_request_context("/admin/settings/"):
        body = render_template(
            "settings/story_transfer.html",
            links={"export_stories": "/api/settings/export-stories"},
        )

    assert 'data-testid="story-export-time-from"' in body
    assert 'data-testid="story-export-time-to"' in body
    assert body.count('x-bind:max="maxDateTimeLocal"') == 2
    assert "maxDateTimeLocal = now.toISOString().slice(0, 16);" in body


@pytest.mark.parametrize("method", ["patch", "post"])
def test_settings_patch_action_sends_only_submitted_fields(app, monkeypatch, method):
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
        method=method.upper(),
        data={"settings[default_collector_proxy]": "http://proxy.test", "settings[onboarding_enabled]": "false"},
    ):
        body, status = cast(tuple[str, int], settings_views.SettingsView.settings_action("/settings/settings", method=method))

    assert status == 200
    assert calls == [
        (
            "/settings/settings",
            {"settings": {"default_collector_proxy": "http://proxy.test", "onboarding_enabled": False}},
        )
    ]
    assert '<span id="notification-message">Successfully updated settings</span>' in body


@pytest.mark.parametrize("enabled", [False, True])
def test_admin_chat_settings_visibility_and_write_only_key(app, enabled):
    from models.admin import Settings, TaranisConfig

    settings = Settings(
        settings=TaranisConfig(
            chat_llm_base_url="https://provider.example/v1", chat_llm_api_key_configured=True, chat_llm_api_format="chat_completions"
        )
    )
    with app.test_request_context("/admin/settings/"):
        body = render_template("settings/settings.html", settings=settings, chat_enabled=enabled, timezone_options=[], frontend_actions=[])

    assert ('data-testid="settings-chat-section"' in body) is enabled
    if enabled:
        assert '<details class="collapse collapse-arrow' in body
        assert 'value="chat_completions" selected' in body
        assert "An API key is saved." in body
        assert 'type="password"' in body
        assert 'value="https://provider.example/v1"' in body
        assert 'data-testid="settings-chat-clear-key"' in body
