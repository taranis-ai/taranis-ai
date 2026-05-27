from flask import render_template, url_for
from models.admin import Settings


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
        body, status = settings_views.SettingsView.settings_action("/settings/export-stories")

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


def test_settings_page_renders_onboarding_reset_button(app):
    with app.test_request_context("/admin/settings/"):
        body = render_template(
            "settings/settings.html",
            settings=Settings(
                settings={
                    "default_collector_proxy": "",
                    "default_collector_interval": "0 */8 * * *",
                    "default_tlp_level": "clear",
                    "default_story_conflict_retention": "200",
                    "default_news_item_conflict_retention": "200",
                    "completed_onboarding_tours": {
                        "admin_welcome_v1": "completed",
                        "admin_advanced_v1": "dismissed",
                    },
                }
            ),
            frontend_actions=[],
        )

    assert 'data-testid="settings-reset-onboarding-tours"' in body
    assert f'hx-post="{url_for("admin_settings.reset_onboarding_tours")}"' in body
    assert 'name="reset_completed_onboarding_tours"' not in body
    assert body.count('name="settings[default_collector_interval]"') == 1


def test_settings_reset_onboarding_tours_patches_core(app, monkeypatch):
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

    with app.test_request_context("/admin/settings/reset-onboarding-tours", method="POST"):
        body, status = settings_views.SettingsView.reset_onboarding_tours()

    assert status == 200
    assert calls == [("/settings/settings", {"reset_completed_onboarding_tours": True})]
    assert '<span id="notification-message">Successfully updated settings</span>' in body


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
        data={"settings[completed_onboarding_tours][admin_welcome_v1]": "completed"},
    ):
        body, status = settings_views.SettingsView.settings_action("/settings/settings", method="patch")

    assert status == 200
    assert calls == [
        (
            "/settings/settings",
            {"settings": {"completed_onboarding_tours": {"admin_welcome_v1": "completed"}}},
        )
    ]
    assert '<span id="notification-message">Successfully updated settings</span>' in body


def test_settings_form_payload_does_not_include_completed_onboarding_tours_when_absent():
    settings = Settings(
        settings={
            "default_collector_proxy": "",
            "default_collector_interval": "0 */8 * * *",
            "default_tlp_level": "clear",
            "default_story_conflict_retention": "200",
            "default_news_item_conflict_retention": "200",
        }
    )

    dumped = settings.model_dump(mode="json")

    assert "completed_onboarding_tours" not in dumped["settings"]
