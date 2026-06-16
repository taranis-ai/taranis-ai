import json
from urllib.parse import parse_qs, urlparse

from flask import url_for
from lxml import html

from frontend.config import Config


def _story_payload(story_id: str = "story-1") -> dict:
    return {
        "id": story_id,
        "title": "Bookmarked Story",
        "description": "Story description",
        "summary": "Story summary",
        "comments": "",
        "attributes": [],
        "links": ["https://example.com/story"],
        "news_items": [
            {
                "id": "news-1",
                "story_id": story_id,
                "title": "Bookmarked News Item",
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


def _bookmark_payload(
    bookmark_id: str = "bookmark-1",
    name: str = "Research",
    story_count: int = 1,
    stories: list[dict] | None = None,
    position: int = 0,
) -> dict:
    story_items = stories if stories is not None else [_story_payload()]
    return {
        "id": bookmark_id,
        "name": name,
        "position": position,
        "created": "2026-06-01T10:00:00",
        "updated": "2026-06-02T10:00:00",
        "story_count": story_count,
        "story_ids": [story["id"] for story in story_items],
        "stories": story_items,
    }


def test_add_to_bookmark_dialog_lists_existing_bookmarks(authenticated_client_basic, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": [_bookmark_payload(story_count=0, stories=[])], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.bookmark_story", story_ids=["story-1", "story-2"]))

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    assert tree.xpath('//dialog[@data-testid="story-bookmark-dialog"]')
    assert tree.xpath('//select[@data-testid="bookmark-select"]/option[@value="bookmark-1"]')[0].text_content() == "Research (0)"
    assert len(tree.xpath('//input[@name="story_ids"]')) == 2


def test_submit_add_to_existing_bookmark_posts_story_ids(authenticated_client_basic, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1/stories",
        json={"message": "2 stories bookmarked", "added": 2, "story_count": 2},
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_bookmark_story"),
        data={"mode": "existing", "bookmark_id": "bookmark-1", "story_ids": ["story-1", "story-2"]},
    )

    assert response.status_code == 200
    assert "2 stories bookmarked" in response.text
    payload = json.loads(responses_mock.calls[0].request.body)
    assert payload == {"story_ids": ["story-1", "story-2"]}


def test_submit_add_to_new_bookmark_creates_then_adds(authenticated_client_basic, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"message": "Bookmark collection created", "id": "bookmark-2", "bookmark": _bookmark_payload(story_count=0, stories=[])},
        status=201,
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-2/stories",
        json={"message": "1 stories bookmarked", "added": 1, "story_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_bookmark_story"),
        data={"mode": "new", "name": "New Research", "story_ids": ["story-1"]},
    )

    assert response.status_code == 200
    assert "1 stories bookmarked" in response.text
    requested_paths = [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks/bookmark-2/stories"]


def test_instant_bookmark_story_uses_first_ordered_bookmark(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": [_bookmark_payload(story_count=0, stories=[])], "total_count": 1},
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1/stories",
        json={"message": "1 stories bookmarked", "added": 1, "story_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.instant_bookmark_story", story_id="story-1"),
        headers=htmx_header,
    )

    assert response.status_code == 200
    assert "1 stories bookmarked" in response.text
    requested_paths = [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks/bookmark-1/stories"]
    bookmark_query = dict(parse_qs(urlparse(responses_mock.calls[0].request.url).query))
    assert bookmark_query == {"limit": ["1"], "order": ["position_asc"]}
    payload = json.loads(responses_mock.calls[1].request.body)
    assert payload == {"story_ids": ["story-1"]}


def test_instant_bookmark_story_creates_default_collection_when_none_exists(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks", json={"items": [], "total_count": 0})
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={
            "message": "Bookmark collection created",
            "id": "bookmark-default",
            "bookmark": _bookmark_payload(bookmark_id="bookmark-default", name="Bookmarks", story_count=0, stories=[]),
        },
        status=201,
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-default/stories",
        json={"message": "1 stories bookmarked", "added": 1, "story_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.instant_bookmark_story", story_id="story-1"),
        headers=htmx_header,
    )

    assert response.status_code == 200
    assert "1 stories bookmarked" in response.text
    requested_paths = [urlparse(call.request.url).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks", "/assess/bookmarks/bookmark-default/stories"]
    create_payload = json.loads(responses_mock.calls[1].request.body)
    assert create_payload == {"name": "Bookmarks"}


def test_bookmarks_page_renders_and_delete_rerenders_list(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": [_bookmark_payload(story_count=0, stories=[])], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.bookmarks"))

    assert response.status_code == 200
    assert "Research" in response.text
    assert 'data-testid="delete-bookmark-bookmark-1"' in response.text

    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1", json={"message": "Bookmark collection deleted"})
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks", json={"items": [], "total_count": 0})

    delete_response = authenticated_client_basic.delete(url_for("assess.bookmark_delete", bookmark_id="bookmark-1"), headers=htmx_header)

    assert delete_response.status_code == 200
    assert "Bookmark collection deleted" in delete_response.text
    assert "No bookmark collections yet." in delete_response.text


def test_bookmark_detail_renders_stories_and_remove_selected(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1", json=_bookmark_payload())
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/filter-lists", json={"tags": [], "sources": [], "groups": [], "languages": []})

    response = authenticated_client_basic.get(url_for("assess.bookmark", bookmark_id="bookmark-1"))

    assert response.status_code == 200
    assert "Bookmarked Story" in response.text
    assert 'data-testid="bookmark-remove-selected"' in response.text

    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1/stories/remove",
        json={"message": "1 stories removed from bookmark collection", "removed": 1, "story_count": 0},
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1", json=_bookmark_payload(story_count=0, stories=[]))

    remove_response = authenticated_client_basic.post(
        url_for("assess.bookmark_remove_stories", bookmark_id="bookmark-1"),
        headers=htmx_header,
        data={"story_ids": ["story-1"]},
    )

    assert remove_response.status_code == 200
    assert "1 stories removed from bookmark collection" in remove_response.text
    assert "This bookmark collection has no stories." in remove_response.text
    payload = json.loads(responses_mock.calls[-2].request.body)
    assert payload == {"story_ids": ["story-1"]}


def test_merge_dialog_renders_selected_bookmarks(authenticated_client_basic, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={
            "items": [
                _bookmark_payload(bookmark_id="bookmark-1", name="Target", story_count=1),
                _bookmark_payload(bookmark_id="bookmark-2", name="Source", story_count=2),
                _bookmark_payload(bookmark_id="bookmark-3", name="Ignored", story_count=3),
            ],
            "total_count": 3,
        },
    )

    response = authenticated_client_basic.get(url_for("assess.bookmark_merge", bookmark_ids=["bookmark-1", "bookmark-2"]))

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    assert tree.xpath('//dialog[@data-testid="bookmark-merge-dialog"]')
    options = tree.xpath('//select[@data-testid="merge-target-bookmark"]/option')
    assert [option.get("value") for option in options] == ["bookmark-1", "bookmark-2"]
    assert "Ignored" not in response.text


def test_merge_dialog_requires_two_selected_bookmarks(authenticated_client_basic):
    response = authenticated_client_basic.get(url_for("assess.bookmark_merge", bookmark_ids=["bookmark-1"]))

    assert response.status_code == 400
    assert "Select at least two bookmark collections to merge." in response.text


def test_submit_merge_dialog_posts_sources_and_rerenders_list(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1/merge",
        json={"message": "2 bookmark collections merged", "merged_bookmark_count": 2, "added": 3, "story_count": 4},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": [_bookmark_payload(bookmark_id="bookmark-1", name="Target", story_count=4)], "total_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_bookmark_merge"),
        headers=htmx_header,
        data={"target_bookmark_id": "bookmark-1", "bookmark_ids": ["bookmark-1", "bookmark-2", "bookmark-3"], "delete_sources": "true"},
    )

    assert response.status_code == 200
    assert "2 bookmark collections merged" in response.text
    assert "Target" in response.text
    payload = json.loads(responses_mock.calls[0].request.body)
    assert payload == {"source_bookmark_ids": ["bookmark-2", "bookmark-3"], "delete_sources": True}


def test_submit_merge_dialog_can_keep_sources(authenticated_client_basic, responses_mock, htmx_header):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1/merge",
        json={"message": "1 bookmark collections merged", "merged_bookmark_count": 1, "added": 1, "story_count": 2},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={
            "items": [
                _bookmark_payload(bookmark_id="bookmark-1", name="Target", story_count=2),
                _bookmark_payload(bookmark_id="bookmark-2", name="Source", story_count=1),
            ],
            "total_count": 2,
        },
    )

    response = authenticated_client_basic.post(
        url_for("assess.submit_bookmark_merge"),
        headers=htmx_header,
        data={"target_bookmark_id": "bookmark-1", "bookmark_ids": ["bookmark-1", "bookmark-2"]},
    )

    assert response.status_code == 200
    payload = json.loads(responses_mock.calls[0].request.body)
    assert payload == {"source_bookmark_ids": ["bookmark-2"], "delete_sources": False}
