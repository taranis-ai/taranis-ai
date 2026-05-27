from flask import url_for

from frontend.config import Config
from frontend.onboarding import ADMIN_ADVANCED_TOUR_ID, ADMIN_WELCOME_TOUR_ID


def settings_response(completed_tours=None):
    return {
        "items": [
            {
                "id": "settings",
                "settings": {
                    "default_collector_proxy": "",
                    "default_collector_interval": "0 */8 * * *",
                    "default_tlp_level": "clear",
                    "default_story_conflict_retention": "200",
                    "default_news_item_conflict_retention": "200",
                    "completed_onboarding_tours": completed_tours or {},
                },
            }
        ]
    }


def test_onboarding_prompt_renders_when_welcome_tour_is_pending(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response(),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-testid="admin-onboarding-tour"' in body
    assert f'data-welcome-tour-id="{ADMIN_WELCOME_TOUR_ID}"' in body
    assert f'data-advanced-tour-id="{ADMIN_ADVANCED_TOUR_ID}"' in body
    assert f'data-settings-action="{url_for("admin_settings.settings_action", action="settings")}"' in body
    assert 'name="settings[default_collector_interval]"' not in body
    assert "data-onboarding-settings-form" not in body
    assert "window.TaranisOnboarding?.startAdminTours" in body


def test_onboarding_prompt_returns_no_content_when_welcome_tour_is_completed(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_WELCOME_TOUR_ID: "dismissed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""


def test_onboarding_prompt_marks_advanced_tour_completed_in_partial(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_ADVANCED_TOUR_ID: "completed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    assert 'data-advanced-completed="true"' in response.get_data(as_text=True)
