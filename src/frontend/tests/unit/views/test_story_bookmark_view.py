import json
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from flask import url_for
from flask.testing import FlaskClient
from lxml import html  # pyright: ignore[reportMissingTypeStubs]
from models.user import UserProfile
from responses import RequestsMock

from frontend.cache import add_user_to_cache
from frontend.config import Config


def _request_url(call: Any) -> str:
    return cast(str, call.request.url)


def _request_json(call: Any) -> Any:
    return json.loads(cast(str | bytes | bytearray, call.request.body))


def _story_payload(story_id: str = "story-1") -> dict[str, Any]:
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
        "read": True,
        "important": True,
        "in_reports_count": 2,
    }


def _bookmark_payload(
    bookmark_id: str = "bookmark-1",
    name: str = "Research",
    story_count: int = 1,
    stories: list[dict[str, Any]] | None = None,
    position: int = 0,
) -> dict[str, Any]:
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


def test_add_to_bookmark_dialog_lists_existing_bookmarks(authenticated_client_basic: FlaskClient, responses_mock: RequestsMock) -> None:
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


def test_submit_add_to_existing_bookmark_posts_story_ids(authenticated_client_basic: FlaskClient, responses_mock: RequestsMock) -> None:
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
    payload = _request_json(responses_mock.calls[0])
    assert payload == {"story_ids": ["story-1", "story-2"]}


def test_submit_add_to_new_bookmark_creates_then_adds(authenticated_client_basic: FlaskClient, responses_mock: RequestsMock) -> None:
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
    requested_paths = [urlparse(_request_url(call)).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks/bookmark-2/stories"]


def test_instant_bookmark_story_uses_first_ordered_bookmark(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
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
    requested_paths = [urlparse(_request_url(call)).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks/bookmark-1/stories"]
    bookmark_query = dict(parse_qs(urlparse(_request_url(responses_mock.calls[0])).query))
    assert bookmark_query == {"limit": ["1"], "order": ["position_asc"]}
    payload = _request_json(responses_mock.calls[1])
    assert payload == {"story_ids": ["story-1"]}


def test_instant_bookmark_story_creates_default_collection_when_none_exists(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
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
    requested_paths = [urlparse(_request_url(call)).path.removeprefix("/api") for call in responses_mock.calls]
    assert requested_paths == ["/assess/bookmarks", "/assess/bookmarks", "/assess/bookmarks/bookmark-default/stories"]
    create_payload = _request_json(responses_mock.calls[1])
    assert create_payload == {"name": "Bookmarks"}


def test_bookmarks_page_renders_and_delete_rerenders_list(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": [_bookmark_payload(story_count=0, stories=[])], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.bookmarks"))

    assert response.status_code == 200
    assert "Research" in response.text
    assert 'data-testid="delete-bookmark-bookmark-1"' in response.text
    assert 'data-testid="reorder-bookmark-bookmark-1"' in response.text

    responses_mock.delete(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1", json={"message": "Bookmark collection deleted"})
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks", json={"items": [], "total_count": 0})

    delete_response = authenticated_client_basic.delete(url_for("assess.bookmark_delete", bookmark_id="bookmark-1"), headers=htmx_header)

    assert delete_response.status_code == 200
    assert "Bookmark collection deleted" in delete_response.text
    assert "No bookmark collections yet." in delete_response.text


def test_reorder_bookmarks_posts_order_and_rerenders_list(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
    responses_mock.patch(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/order", json={"message": "Bookmark order updated"})
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={
            "items": [
                _bookmark_payload(bookmark_id="bookmark-2", name="Second", story_count=0, stories=[], position=0),
                _bookmark_payload(bookmark_id="bookmark-1", name="First", story_count=0, stories=[], position=1),
            ],
            "total_count": 2,
        },
    )

    response = authenticated_client_basic.patch(
        url_for("assess.bookmark_reorder"),
        headers=htmx_header,
        data={"bookmark_ids": ["bookmark-2", "bookmark-1"]},
    )

    assert response.status_code == 200
    assert "Bookmark order updated" in response.text
    assert response.text.index("Second") < response.text.index("First")
    payload = _request_json(responses_mock.calls[0])
    assert payload == {"bookmark_ids": ["bookmark-2", "bookmark-1"]}


def test_bookmark_detail_renders_stories_and_remove_selected(
    authenticated_client_basic: FlaskClient,
    auth_user_basic: UserProfile,
    responses_mock: RequestsMock,
    htmx_header: dict[str, bool],
) -> None:
    compact_user = auth_user_basic.model_copy(deep=True)
    compact_user.profile.compact_view = True
    add_user_to_cache(compact_user.model_dump(mode="json"))
    embedded_story = _story_payload()
    embedded_story.pop("in_reports_count")
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1",
        json=_bookmark_payload(stories=[embedded_story]),
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/filter-lists", json={"tags": [], "sources": [], "groups": [], "languages": []})
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories",
        json={"items": [_story_payload()], "total_count": 1},
    )

    response = authenticated_client_basic.get(url_for("assess.bookmark", bookmark_id="bookmark-1"))

    assert response.status_code == 200
    assert "Bookmarked Story" in response.text
    tree = html.fromstring(response.text)
    story_card = tree.xpath('//article[@data-testid="story-card-story-1"]')[0]
    assert story_card.get("data-story-detail-view") == "false"
    assert story_card.get("data-story-read") == "true"
    assert story_card.get("data-story-important") == "true"
    assert "bookmark_id=bookmark-1" in story_card.xpath('.//*[@data-testid="toggle-read"]')[0].get("hx-put")
    assert "bookmark_id=bookmark-1" in story_card.xpath('.//*[@data-testid="toggle-important"]')[0].get("hx-put")
    ungroup_story = story_card.xpath('.//*[@data-testid="ungroup-story"]')[0]
    assert "bookmark_id=bookmark-1" in ungroup_story.get("hx-post")
    assert ungroup_story.get("hx-target") == "#bookmark-detail-container"
    assert "Read" in story_card.text_content()
    assert "Important" in story_card.text_content()
    assert "In Reports" in story_card.text_content()
    assert tree.xpath('//*[@data-testid="assess-select-all-button"]')
    assert not tree.xpath('//*[@data-testid="assess-tob-bar-actions-menu"]')
    assert "Shift+B" not in response.text
    selection_form = tree.xpath('//form[@id="bookmark-selection-form"]')[0]
    assert selection_form.xpath('./input[@name="bookmark_id" and @value="bookmark-1"]')
    assert selection_form.xpath('.//input[@type="checkbox" and @name="story_ids" and @value="story-1"]')
    for action in ("bulk-toggle-read", "bulk-toggle-important"):
        assert tree.xpath(f'//*[@data-testid="{action}"]')[0].get("hx-include") == "#bookmark-selection-form"
    for action_url in (url_for("assess.cluster_story"), url_for("assess.report_story")):
        assert tree.xpath(f'//*[@hx-get="{action_url}"]')[0].get("hx-include") == "#bookmark-selection-form"
    remove_selected = selection_form.xpath('.//button[@type="button" and @data-testid="bookmark-remove-selected"]')[0]
    assert remove_selected.get("hx-include") == "#bookmark-selection-form"
    assert remove_selected.get("hx-confirm") == "Remove selected stories from this bookmark collection?"
    assert not tree.xpath('//*[@data-testid="bookmark-story"]')
    story_request = next(call for call in responses_mock.calls if urlparse(_request_url(call)).path.endswith("/assess/stories"))
    assert parse_qs(urlparse(_request_url(story_request)).query)["story_ids"] == ["story-1"]

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
    payload = _request_json(responses_mock.calls[-2])
    assert payload == {"story_ids": ["story-1"]}


def test_bookmark_cluster_dialog_offers_cluster_and_open(authenticated_client_basic: FlaskClient, responses_mock: RequestsMock) -> None:
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stories/story-1", json=_story_payload())
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stories/story-2", json=_story_payload("story-2"))

    response = authenticated_client_basic.get(
        url_for(
            "assess.cluster_story",
            story_ids=["story-1", "story-2"],
            bookmark_id="bookmark-1",
        )
    )

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    assert tree.xpath('//input[@name="bookmark_id" and @value="bookmark-1"]')
    assert tree.xpath('//*[@data-testid="dialog-story-cluster-submit"]')
    assert tree.xpath('//*[@data-testid="dialog-story-cluster-open"]')


def test_bookmark_story_action_keeps_bookmark_card_behavior(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
    responses_mock.patch(
        f"{Config.TARANIS_CORE_URL}/assess/stories/story-1",
        json={"message": "Story updated"},
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stories/story-1", json=_story_payload())
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": [], "languages": []},
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks", json={"items": [], "total_count": 0})

    response = authenticated_client_basic.put(
        url_for("assess.story", story_id="story-1", bookmark_id="bookmark-1"),
        headers={**htmx_header, "HX-Current-URL": url_for("assess.bookmark", bookmark_id="bookmark-1", _external=True)},
        data={"read": "false"},
    )

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    story_card = tree.xpath('//article[@data-testid="story-card-story-1"]')[0]
    assert not story_card.xpath('.//*[@data-testid="bookmark-story"]')
    assert "bookmark_id=bookmark-1" in story_card.xpath('.//*[@data-testid="toggle-read"]')[0].get("hx-put")


def test_bookmark_ungroup_error_stays_in_bookmark(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
    responses_mock.put(
        f"{Config.TARANIS_CORE_URL}/assess/stories/ungroup",
        json={"error": "Story is assigned to a report"},
        status=400,
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks/bookmark-1", json=_bookmark_payload())
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": [], "languages": []},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories",
        json={"items": [_story_payload()], "total_count": 1},
    )

    response = authenticated_client_basic.post(
        url_for("assess.ungroup", story_id="story-1", bookmark_id="bookmark-1"),
        headers=htmx_header,
    )

    assert response.status_code == 200
    assert "Story is assigned to a report" in response.text
    assert 'data-testid="bookmark-detail"' in response.text
    assert "HX-Redirect" not in response.headers
    assert _request_json(responses_mock.calls[0]) == ["story-1"]


def test_story_edit_from_bookmark_returns_to_bookmark(
    authenticated_client_basic: FlaskClient, responses_mock: RequestsMock, htmx_header: dict[str, bool]
) -> None:
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/stories/story-1", json=_story_payload())
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": [], "languages": []},
    )
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/assess/bookmarks", json={"items": [], "total_count": 0})
    responses_mock.patch(
        f"{Config.TARANIS_CORE_URL}/assess/stories/story-1",
        json={"message": "Story updated"},
    )

    edit_response = authenticated_client_basic.get(url_for("assess.story_edit", story_id="story-1", bookmark_id="bookmark-1"))

    assert edit_response.status_code == 200
    tree = html.fromstring(edit_response.text)
    edit_form_url = tree.xpath('//form[@id="story-edit-form"]')[0].get("hx-post")
    assert parse_qs(urlparse(edit_form_url).query) == {
        "bookmark_id": ["bookmark-1"],
        "return_to_bookmark": ["1"],
    }
    assert "Return to bookmark" in edit_response.text

    dislike_url = tree.xpath('//button[.//span[normalize-space()="Dislike"]]')[0].get("hx-post")
    vote_response = authenticated_client_basic.post(
        dislike_url,
        headers={
            **htmx_header,
            "HX-Current-URL": url_for(
                "assess.story_edit",
                story_id="story-1",
                bookmark_id="bookmark-1",
                _external=True,
            ),
        },
        data={"vote": "dislike"},
    )

    assert vote_response.status_code == 200
    assert "Return to bookmark" in vote_response.text
    vote_tree = html.fromstring(vote_response.text)
    edit_form_url = vote_tree.xpath('//form[@id="story-edit-form"]')[0].get("hx-post")
    assert parse_qs(urlparse(edit_form_url).query) == {
        "bookmark_id": ["bookmark-1"],
        "return_to_bookmark": ["1"],
    }

    response = authenticated_client_basic.post(
        edit_form_url,
        headers=htmx_header,
        data={"title": "Updated bookmarked story"},
    )

    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == url_for("assess.bookmark", bookmark_id="bookmark-1")
