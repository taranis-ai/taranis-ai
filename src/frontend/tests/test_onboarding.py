from flask import session, url_for

from frontend.config import Config
from frontend.onboarding import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_ONBOARDING_SESSION_KEY,
    ADMIN_WELCOME_TOUR_ID,
    update_admin_onboarding_session_from_settings_payload,
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
    assert "self.TaranisOnboarding?.startAdminTours" in body


def test_onboarding_prompt_renders_when_advanced_tour_is_pending(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_WELCOME_TOUR_ID: "completed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-welcome-completed="true"' in body
    assert 'data-advanced-completed="false"' in body


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


def test_onboarding_prompt_treats_non_completed_values_as_pending(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_WELCOME_TOUR_ID: "dismissed", ADMIN_ADVANCED_TOUR_ID: "dismissed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-welcome-completed="false"' in body
    assert 'data-advanced-completed="false"' in body


def test_onboarding_prompt_marks_advanced_tour_completed_in_partial(app, authenticated_client, responses):
    responses.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json=settings_response({ADMIN_ADVANCED_TOUR_ID: "completed"}),
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'data-advanced-completed="true"' in body
    assert 'data-welcome-completed="false"' in body


def test_update_admin_onboarding_session_handles_reset_payload(app):
    with app.test_request_context("/"):
        session[ADMIN_ONBOARDING_SESSION_KEY] = {
            "welcome_tour_id": ADMIN_WELCOME_TOUR_ID,
            "advanced_tour_id": ADMIN_ADVANCED_TOUR_ID,
            "welcome_completed": True,
            "advanced_completed": True,
        }

        update_admin_onboarding_session_from_settings_payload({"reset_onboarding_tours": True})

        context = session[ADMIN_ONBOARDING_SESSION_KEY]
        assert context["welcome_completed"] is False
        assert context["advanced_completed"] is False
