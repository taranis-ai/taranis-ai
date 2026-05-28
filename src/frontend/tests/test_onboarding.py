import pytest
from flask import url_for

from frontend.config import Config
from frontend.onboarding import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_WELCOME_TOUR_ID,
    is_onboarding_tour_completed,
)


def settings_response(onboarding_tours=None):
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
                    "onboarding_tours": onboarding_tours or {},
                },
            }
        ]
    }


def test_onboarding_prompt_renders_pending_context(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_ADVANCED_TOUR_ID: "completed"}),
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
    assert 'data-welcome-completed="false"' in body
    assert 'data-advanced-completed="true"' in body
    assert 'name="settings[default_collector_interval]"' not in body
    assert "data-onboarding-settings-form" not in body
    assert "self.TaranisOnboarding?.startAdminTours" in body


def test_onboarding_prompt_returns_no_content_when_all_tours_are_completed(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_WELCOME_TOUR_ID: "completed", ADMIN_ADVANCED_TOUR_ID: "completed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""


@pytest.mark.parametrize(
    ("status", "completed"),
    [
        ("completed", True),
        ("dismissed", False),
        ("", False),
    ],
)
def test_onboarding_tour_completion_status(status, completed):
    assert is_onboarding_tour_completed({ADMIN_WELCOME_TOUR_ID: status}, ADMIN_WELCOME_TOUR_ID) is completed
