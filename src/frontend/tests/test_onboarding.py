import json

from flask import render_template, url_for
from models.user import (
    ADMIN_ADVANCED_TOUR_ID,
    ADMIN_WELCOME_TOUR_ID,
    USER_PRODUCT_OVERVIEW_TASK_ID,
    OnboardingTask,
    ProfileSettings,
)

from frontend.cache import add_user_to_cache
from frontend.config import Config


def _cache_user_with_pending_tasks(user, pending_tasks):
    updated_user = user.model_copy(update={"pending_onboarding_tasks": pending_tasks})
    add_user_to_cache(updated_user.model_dump(mode="json"))


def test_onboarding_prompt_renders_pending_context(app, authenticated_client, auth_user, responses):
    _cache_user_with_pending_tasks(
        auth_user,
        [
            OnboardingTask(id=ADMIN_WELCOME_TOUR_ID, scope="global"),
            OnboardingTask(id=USER_PRODUCT_OVERVIEW_TASK_ID, scope="user"),
        ],
    )

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 200
    assert len(responses.calls) == 0
    body = response.get_data(as_text=True)
    assert 'data-testid="onboarding-root"' in body
    assert f'data-profile-action="{url_for("user.settings")}"' in body
    assert "data-pending-tasks=" in body
    assert ADMIN_WELCOME_TOUR_ID in body
    assert USER_PRODUCT_OVERVIEW_TASK_ID in body
    assert ADMIN_ADVANCED_TOUR_ID not in body
    assert "settings[default_collector_interval]" not in body


def test_onboarding_prompt_returns_no_content_when_all_tasks_completed(app, authenticated_client, auth_user, responses):
    _cache_user_with_pending_tasks(auth_user, [])

    response = authenticated_client.get(url_for("base.onboarding_prompt"))

    assert response.status_code == 204
    assert response.get_data(as_text=True) == ""
    assert len(responses.calls) == 0


def test_base_template_can_render_without_pending_onboarding(app):
    with app.test_request_context("/"):
        body = render_template("base.html")

    assert "onboarding-root" not in body


def test_onboarding_completion_posts_profile_task(authenticated_client, responses, monkeypatch):
    from frontend.views import user_views

    monkeypatch.setattr(user_views, "update_current_user_cache", lambda: None)
    responses.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={"message": "Profile updated", "user_profile": {"onboarding_tasks": {ADMIN_WELCOME_TOUR_ID: "completed"}}},
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.post(
        url_for("user.update_settings"),
        data={f"onboarding_tasks[{ADMIN_WELCOME_TOUR_ID}]": "completed"},
    )

    assert response.status_code == 200
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert set(request_body) == {"onboarding_tasks"}
    assert request_body["onboarding_tasks"][ADMIN_WELCOME_TOUR_ID] == "completed"


def test_user_onboarding_reset_posts_empty_profile_tasks(authenticated_client, responses, monkeypatch):
    from frontend.views import user_views

    monkeypatch.setattr(user_views, "update_current_user_cache", lambda: None)
    responses.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={"message": "Profile updated", "user_profile": {"onboarding_tasks": {}}},
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.post(url_for("user.update_settings"), data={"reset_onboarding_tasks": "true"})

    assert response.status_code == 200
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body == {"onboarding_tasks": {}}
    assert 'data-testid="user-reset-onboarding-tours"' in response.get_data(as_text=True)
    assert '<span id="notification-message">Profile updated</span>' in response.get_data(as_text=True)


def test_user_settings_update_preserves_onboarding_task_status(authenticated_client_basic, auth_user_basic, responses, monkeypatch):
    from frontend.views import user_views

    monkeypatch.setattr(user_views, "update_current_user_cache", lambda: None)
    _cache_user_with_pending_tasks(
        auth_user_basic.model_copy(update={"profile": ProfileSettings(onboarding_tasks={USER_PRODUCT_OVERVIEW_TASK_ID: "completed"})}),
        [],
    )
    responses.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={"message": "Profile updated", "user_profile": {"compact_view": True}},
        status=200,
        content_type="application/json",
    )

    response = authenticated_client_basic.post(
        url_for("user.update_settings"),
        data={"compact_view": "true"},
    )

    assert response.status_code == 200
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["compact_view"] is True
    assert "onboarding_tasks" not in request_body
