import json
from urllib.parse import urlparse

from flask import url_for
from lxml import html

from frontend.config import Config


def _story_payload(story_id: str = "story-1") -> dict:
    return {
        "id": story_id,
        "title": "Stashed Story",
        "description": "Story description",
        "summary": "Story summary",
        "comments": "",
        "attributes": [],
        "links": ["https://example.com/story"],
        "news_items": [
            {
                "id": "news-1",
                "story_id": story_id,
                "title": "Stashed News Item",
                "content": "News content",
                "link": "https://example.com/story",
                "source": "manual",
                "osint_source_id": "manual",
                "published": "2026-06-01T10:00:00",
                "collected": "2026-06-01T10:00:00",
                "tags": [],
            }
        ],
        "tags": [],
    }


def _stash_payload(story_count: int = 1, stories: list[dict] | None = None) -> dict:
    story_items = stories if stories is not None else [_story_payload()]
    return {
        "id": "stash-1",
        "name": "Research",
        "created": "2026-06-01T10:00:00",
        "updated": "2026-06-02T10:00:00",
        "story_count": story_count,
        "story_ids": [story["id"] for story in story_items],
        "stories": story_items,
    }


def test_add_to_stash_dialog_lists_existing_stashes(authenticated_client_basic, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stashes",
        json={"items": [_stash_payload(story_count=0, stories=[])], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.stash_story", story_ids=["story-1", "story-2"]))

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    assert tree.xpath('//dialog[@data-testid="story-stash-dialog"]')
    assert tree.xpath('//select[@data-testid="stash-select"]/option[@value="stash-1"]')[0].text_content() == "Research (0)"
    assert len(tree.xpath('//input[@name="story_ids"]')) == 2


def test_submit_add_to_existing_stash_posts_story_ids(authenticated_client_basic, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-1/stories",
        json={"message": "2 stories added to stash", "added": 2, "story_count": 2},
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_stash_story"),
        data={"mode": "existing", "stash_id": "stash-1", "story_ids": ["story-1", "story-2"]},
    )

    assert response.status_code == 200
    assert "2 stories added to stash" in response.text
    payload = json.loads(responses_mock.calls[0].request.body)
    assert payload == {"story_ids": ["story-1", "story-2"]}


def test_submit_add_to_new_stash_creates_then_adds(authenticated_client_basic, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/stashes",
        json={"message": "Stash created", "id": "stash-2", "stash": _stash_payload(story_count=0, stories=[])},
        status=201,
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-2/stories",
        json={"message": "1 stories added to stash", "added": 1, "story_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_stash_story"),
        data={"mode": "new", "name": "New Research", "story_ids": ["story-1"]},
    )

    assert response.status_code == 200
    assert "1 stories added to stash" in response.text
    requested_paths = [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/stashes", "/assess/stashes/stash-2/stories"]


def test_stashes_page_renders_and_delete_rerenders_list(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stashes",
        json={"items": [_stash_payload(story_count=0, stories=[])], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.stashes"))

    assert response.status_code == 200
    assert "Research" in response.text
    assert 'data-testid="delete-stash-stash-1"' in response.text

    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-1", json={"message": "Stash deleted"})
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stashes", json={"items": [], "total_count": 0})

    delete_response = authenticated_client_basic.delete(url_for("assess.stash_delete", stash_id="stash-1"), headers=htmx_header)

    assert delete_response.status_code == 200
    assert "Stash deleted" in delete_response.text
    assert "No stashes yet." in delete_response.text


def test_stash_detail_renders_stories_and_remove_selected(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-1", json=_stash_payload())
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/filter-lists", json={"tags": [], "sources": [], "groups": [], "languages": []})

    response = authenticated_client_basic.get(url_for("assess.stash", stash_id="stash-1"))

    assert response.status_code == 200
    assert "Stashed Story" in response.text
    assert 'data-testid="stash-remove-selected"' in response.text

    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-1/stories/remove",
        json={"message": "1 stories removed from stash", "removed": 1, "story_count": 0},
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stashes/stash-1", json=_stash_payload(story_count=0, stories=[]))

    remove_response = authenticated_client_basic.post(
        url_for("assess.stash_remove_stories", stash_id="stash-1"),
        headers=htmx_header,
        data={"story_ids": ["story-1"]},
    )

    assert remove_response.status_code == 200
    assert "1 stories removed from stash" in remove_response.text
    assert "This stash has no stories." in remove_response.text
    payload = json.loads(responses_mock.calls[-2].request.body)
    assert payload == {"story_ids": ["story-1"]}
