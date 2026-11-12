from urllib.parse import urlparse

from models.user import UserProfile

from frontend.cache import add_user_to_cache, cache
from frontend.config import Config
from frontend.views.analyst_review_views import ANALYST_REVIEW_PERMISSIONS


def enable_analyst_review(user: UserProfile) -> None:
    review_user = user.model_copy(deep=True)
    review_user.permissions = sorted(set(review_user.permissions) | ANALYST_REVIEW_PERMISSIONS)
    add_user_to_cache(review_user.model_dump(mode="json"))


def review_state(story_ids: list[str]) -> dict:
    return {
        "report_id": "report-1",
        "report_title": "Shift Report",
        "story_ids": story_ids,
        "total": len(story_ids),
        "reviewed": 0,
        "added": 0,
        "review_report": False,
    }


def mock_story(responses_mock, story_id: str, title: str) -> None:
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}",
        json={
            "id": story_id,
            "title": title,
            "summary": f"Summary for {title}",
            "news_items": [],
            "links": [],
            "important": False,
            "read": False,
        },
    )


def test_start_creates_fixed_review_snapshot(authenticated_client, auth_user, responses_mock):
    enable_analyst_review(auth_user)
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/analyze/report-items",
        json={
            "report": {
                "id": "report-1",
                "title": "Shift Report",
                "completed": False,
                "report_item_type_id": "type-1",
                "stories": [],
                "grouped_attributes": [],
            }
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/analyst-review/snapshot",
        json={"story_ids": ["story-1", "story-2"]},
    )

    response = authenticated_client.post(
        "/analyst-review/start",
        data={"mode": "new", "title": "Shift Report", "report_item_type_id": "type-1"},
    )

    assert response.status_code == 302
    run_id = urlparse(response.location).path.rsplit("/", 1)[-1]
    state = cache.get(f"{cache.key_prefix}:analyst-review:{auth_user.username}:{run_id}")
    assert state == review_state(["story-1", "story-2"])


def test_failed_mutation_does_not_advance_review(authenticated_client, auth_user, responses_mock):
    enable_analyst_review(auth_user)
    run_id = "failed-action"
    state = review_state(["story-1", "story-2"])
    cache.set(f"{cache.key_prefix}:analyst-review:{auth_user.username}:{run_id}", state)
    mock_story(responses_mock, "story-1", "First Story")
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/analyst-review/actions",
        json={"error": "Failed to apply analyst review action"},
        status=500,
    )

    response = authenticated_client.post(
        f"/analyst-review/{run_id}/actions",
        data={"action": "add"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 500
    assert "First Story" in response.get_data(as_text=True)
    assert cache.get(f"{cache.key_prefix}:analyst-review:{auth_user.username}:{run_id}") == state


def test_skip_advances_without_persisting_story(authenticated_client, auth_user, responses_mock):
    enable_analyst_review(auth_user)
    run_id = "skip-action"
    cache.set(
        f"{cache.key_prefix}:analyst-review:{auth_user.username}:{run_id}",
        review_state(["story-1", "story-2"]),
    )
    mock_story(responses_mock, "story-1", "First Story")
    mock_story(responses_mock, "story-2", "Second Story")

    response = authenticated_client.post(
        f"/analyst-review/{run_id}/actions",
        data={"action": "skip"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Second Story" in html
    assert "1 of 2 reviewed" in html
    assert not [call for call in responses_mock.calls if call.request.method == "POST"]
    state = cache.get(f"{cache.key_prefix}:analyst-review:{auth_user.username}:{run_id}")
    assert state["story_ids"] == ["story-2"]
    assert state["reviewed"] == 1
