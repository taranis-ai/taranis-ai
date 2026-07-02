import json
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from flask import render_template, render_template_string, url_for
from lxml import html
from models.assess import FilterLists, Story, StoryUpdatePayload
from models.user import AssessSavedFilter
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import Forbidden

from frontend.cache import add_user_to_cache
from frontend.config import Config
from frontend.views.story_views import ASSESS_SAVED_FILTER_SESSION_KEY, StoryView, _normalize_story_import_payload


def expected_search_trigger(input_id: str) -> str:
    return f"input changed delay:500ms from:#{input_id}, search from:#{input_id}"


def mock_story_for_edit(responses_mock, story_payload: dict):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": []},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_payload['id']}",
        json=story_payload,
    )


def story_with_news_item_tags() -> dict:
    return {
        "id": "story-1",
        "title": "Tagged Story",
        "description": "Story description",
        "summary": "Story summary",
        "comments": "Story comment",
        "attributes": [],
        "news_items": [
            {
                "id": "news-1",
                "story_id": "story-1",
                "title": "Tagged News Item",
                "content": "News item content",
                "source": "manual",
                "osint_source_id": "manual",
                "tags": [{"name": "item-tag", "tag_type": "actor"}],
            }
        ],
    }


def _bookmark_collection_payload(bookmark_id: str, name: str, story_count: int, position: int = 0) -> dict:
    return {
        "id": bookmark_id,
        "name": name,
        "position": position,
        "created": "2026-06-01T10:00:00",
        "updated": "2026-06-02T10:00:00",
        "story_count": story_count,
        "story_ids": [],
        "stories": [],
    }


def _profile_update_payload(responses_mock: Any) -> dict[str, Any]:
    profile_update_call = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/users/profile"))
    request_body = profile_update_call.request.body
    return json.loads(request_body.decode() if isinstance(request_body, bytes) else request_body)


def _cache_saved_filters(auth_user: Any, saved_filters: list[AssessSavedFilter]) -> None:
    saved_user = auth_user.model_copy(deep=True)
    saved_user.profile.assess_saved_filters = saved_filters
    add_user_to_cache(saved_user.model_dump(mode="json"))


def _mock_profile_update(responses_mock: Any) -> None:
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={"message": "Profile updated", "id": "user-1", "user_profile": {"assess_saved_filters": []}},
    )


def test_story_diff_view_renders_compare_payload(app, authenticated_client, responses_mock):
    story_id = "story-1"
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}/revisions/1",
        json={
            "id": "revision-1",
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": "user-1",
            "note": "created",
            "data": {
                "title": "Kill Chain im Krieg verkurzt",
                "description": "First draft",
                "summary": "Summary A",
                "comments": "Comment A",
                "likes": 1,
                "dislikes": 0,
                "tags": [{"name": "old-tag"}],
                "news_items": [{"id": "news-1", "title": "Old news"}],
                "attributes": [{"key": "TLP", "value": "clear"}],
            },
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}/revisions/2",
        json={
            "id": "revision-2",
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": "user-2",
            "note": "update",
            "data": {
                "title": "Kill Chain im Krieg deutlich verkurzt",
                "description": "First draft",
                "summary": "Summary B",
                "comments": "Comment A",
                "likes": 3,
                "dislikes": 1,
                "tags": [{"name": "new-tag"}],
                "news_items": [{"id": "news-2", "title": "New news"}],
                "attributes": [{"key": "TLP", "value": "amber"}],
            },
        },
        status=200,
        content_type="application/json",
    )

    with app.test_request_context():
        response = authenticated_client.get(url_for("assess.story_diff", story_id=story_id, from_rev=1, to_rev=2))

    assert response.status_code == 200
    html_doc = response.get_data(as_text=True)
    assert "Changes:" in html_doc
    assert "Kill Chain im Krieg deutlich verkurzt" in html_doc
    assert "old_segments" not in html_doc
    assert "deutlich " in html_doc
    assert "bg-success/20 text-success" in html_doc
    assert "bg-error/20 text-error" in html_doc
    assert "Likes" in html_doc
    assert "Dislikes" in html_doc


def test_story_diff_view_shows_no_changes_state(app, authenticated_client, responses_mock):
    story_id = "story-1"
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}/revisions/1",
        json={
            "id": "revision-1",
            "revision": 1,
            "created_at": "2026-03-12T10:00:00",
            "created_by": "alice",
            "created_by_id": "user-1",
            "note": "created",
            "data": {
                "title": "Story title",
                "tags": [],
                "news_items": [],
                "attributes": [],
                "description": "",
                "summary": "",
                "comments": "",
            },
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}/revisions/2",
        json={
            "id": "revision-2",
            "revision": 2,
            "created_at": "2026-03-12T11:00:00",
            "created_by": "bob",
            "created_by_id": "user-2",
            "note": "update",
            "data": {
                "title": "Story title",
                "tags": [],
                "news_items": [],
                "attributes": [],
                "description": "",
                "summary": "",
                "comments": "",
            },
        },
        status=200,
        content_type="application/json",
    )

    with app.test_request_context():
        response = authenticated_client.get(url_for("assess.story_diff", story_id=story_id, from_rev=1, to_rev=2))

    assert response.status_code == 200
    html_doc = response.get_data(as_text=True)
    assert "No changes detected between these revisions." in html_doc


def test_normalize_story_import_payload_unwraps_export_items():
    payload = {"total_count": 1, "items": [{"id": "story-1", "news_items": [{"id": "news-1"}]}]}

    normalized = _normalize_story_import_payload(payload)

    assert normalized == [{"id": "story-1", "news_items": [{"id": "news-1", "story_id": "story-1"}]}]


def test_normalize_story_import_payload_keeps_raw_story_list():
    payload = [{"id": "story-1", "news_items": [{"id": "news-1"}]}]

    normalized = _normalize_story_import_payload(payload)

    assert normalized == [{"id": "story-1", "news_items": [{"id": "news-1", "story_id": "story-1"}]}]


def test_normalize_story_import_payload_strips_export_only_fields():
    payload = {
        "total_count": 1,
        "items": [
            {
                "id": "story-1",
                "title": "Imported Story",
                "relevance_override": 7,
                "user_vote": "like",
                "in_reports_count": 3,
                "updated": "2026-03-12T10:00:00",
                "links": ["https://example.com/story"],
                "news_items": [
                    {
                        "id": "news-1",
                        "title": "Imported Story News 1",
                        "source": "https://example.com/source",
                        "content": "content",
                        "osint_source_id": "99",
                        "updated": "2026-03-12T10:00:00",
                        "tags": [{"name": "news-tag", "tag_type": "misc"}],
                    }
                ],
            }
        ],
    }

    normalized = _normalize_story_import_payload(payload)

    assert normalized == [
        {
            "id": "story-1",
            "title": "Imported Story",
            "relevance_override": 7,
            "news_items": [
                {
                    "id": "news-1",
                    "title": "Imported Story News 1",
                    "source": "https://example.com/source",
                    "content": "content",
                    "osint_source_id": "99",
                    "tags": [{"name": "news-tag", "tag_type": "misc"}],
                    "story_id": "story-1",
                }
            ],
        }
    ]


def test_story_to_core_dict_strips_export_only_fields():
    story = Story.model_validate(
        {
            "id": "story-1",
            "title": "Imported Story",
            "updated": "2026-03-12T10:00:00",
            "links": ["https://example.com/story"],
            "relevance_override": 7,
            "user_vote": "like",
            "in_reports_count": 3,
            "news_items": [
                {
                    "osint_source_id": "manual",
                    "title": "Imported Story News 1",
                    "links": ["https://example.com/news"],
                    "tags": [{"name": "news-tag", "tag_type": "misc"}],
                }
            ],
        }
    )

    normalized = story.to_core_dict()

    assert normalized["relevance_override"] == 7
    assert "updated" not in normalized
    assert "links" not in normalized
    assert "user_vote" not in normalized
    assert "in_reports_count" not in normalized
    assert "links" not in normalized["news_items"][0]
    assert normalized["news_items"][0]["tags"] == [{"name": "news-tag", "tag_type": "misc"}]


def test_story_update_payload_ignores_tags():
    payload = StoryUpdatePayload.model_validate({"title": "Updated Story", "tags": [{"name": "story-tag", "tag_type": "misc"}]})

    assert payload.model_dump(mode="json") == {"title": "Updated Story"}


def _render_news_item_card(story: Story) -> str:
    return render_template_string(
        '{% from "assess/news_item_card.html" import news_item_card %}{{ news_item_card(story.news_items[0], story) }}',
        story=story,
    )


def test_news_item_card_shows_author_when_present(app):
    story = Story.model_validate(
        {
            "id": "story-1",
            "title": "Story with author",
            "news_items": [
                {
                    "id": "news-1",
                    "story_id": "story-1",
                    "osint_source_id": "manual",
                    "title": "News with author",
                    "author": "James Bond",
                }
            ],
        }
    )

    with app.test_request_context():
        markup = _render_news_item_card(story)

    tree = html.fromstring(markup)
    author_badge = tree.xpath('//*[@data-test-id="news-item-author"]')
    assert len(author_badge) == 1
    assert author_badge[0].text_content().strip() == "Author · James Bond"


def test_news_item_card_hides_author_when_missing_or_empty(app):
    for payload in ({}, {"author": ""}):
        story = Story.model_validate(
            {
                "id": "story-1",
                "title": "Story without author",
                "news_items": [
                    {
                        "id": "news-1",
                        "story_id": "story-1",
                        "osint_source_id": "manual",
                        "title": "News without author",
                        **payload,
                    }
                ],
            }
        )

        with app.test_request_context():
            markup = _render_news_item_card(story)

        tree = html.fromstring(markup)
        assert not tree.xpath('//*[@data-test-id="news-item-author"]')
        assert "Author ·" not in tree.text_content()


def test_manual_news_item_form_routes_htmx_errors_to_notification_bar(authenticated_client):
    response = authenticated_client.get(url_for("assess.get_news_item", news_item_id="0"))

    assert response.status_code == 200

    tree = html.fromstring(response.text)
    form = tree.xpath('//form[@id="news-item-form"]')
    file_form = tree.xpath('//form[@hx-encoding="multipart/form-data"]')
    url_form = tree.xpath('//form[@id="news-item-create-from-url-form"]')
    url_parameters_dialog = tree.xpath('//dialog[@id="create_from_url_parameters_dialog"]')

    assert len(form) == 1
    assert form[0].get("hx-target-error") == "#notification-bar"
    assert len(file_form) == 1
    assert file_form[0].get("hx-target-error") == "#notification-bar"
    assert len(url_form) == 1
    assert url_form[0].get("hx-target-error") == "#notification-bar"
    assert url_form[0].xpath('.//input[@name="fetch_url"]')
    assert len(url_parameters_dialog) == 1
    assert url_parameters_dialog[0].xpath('.//*[@name="parameters[XPATH]"]')
    assert url_parameters_dialog[0].xpath('.//*[@name="parameters[BROWSER_MODE]"]')
    additional_headers_input = url_parameters_dialog[0].xpath('.//input[@name="parameters[ADDITIONAL_HEADERS]"]')
    assert len(additional_headers_input) == 1
    assert not url_parameters_dialog[0].xpath('.//textarea[@name="parameters[ADDITIONAL_HEADERS]"]')

    source_input = form[0].xpath('.//input[@name="source"]')
    assert len(source_input) == 1
    assert source_input[0].get("required") is None


def test_manual_news_item_validation_error_targets_notification_bar(authenticated_client):
    response = authenticated_client.post(
        url_for("assess.create_news_item"),
        data={
            "title": "Invalid language test",
            "link": "http://blubb.xxx",
            "language": "xx",
            "osint_source_id": "manual",
        },
    )

    assert response.status_code == 400
    assert response.headers["HX-Retarget"] == "#notification-bar"
    assert response.headers["HX-Reswap"] == "outerHTML"
    tree = html.fromstring(response.text)
    notification_bar = tree.xpath('//section[@id="notification-bar"]')[0]
    assert notification_bar.get("hx-swap-oob") is None
    assert "Invalid BCP 47 language tag" in notification_bar.text_content()


def test_story_edit_renders_news_item_tag_editor(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    mock_story_for_edit(responses_mock, story_payload)

    response = authenticated_client.get(url_for("assess.story_edit", story_id=story_payload["id"]))

    assert response.status_code == 200
    tree = html.fromstring(response.text)

    assert tree.xpath('//*[@data-testid="edit-newsitem-tags"]')
    assert tree.xpath('//*[@data-testid="news-item-tag-name-input"]')
    assert "keydown[canUseAssessShortcut(event, 'r')]" in response.text
    assert "resetTags(); tagEditorOpen = false" in response.text
    assert not tree.xpath('//*[@data-testid="tag-name-input"]')
    assert not tree.xpath('//*[@data-testid="tag-value-input"]')


def test_story_edit_advanced_view_renders_sentiment_status_chip(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    story_payload["attributes"] = [
        {"key": "cybersecurity", "value": "yes"},
        {"key": "sentiment", "value": "negative"},
    ]
    mock_story_for_edit(responses_mock, story_payload)

    response = authenticated_client.get(url_for("assess.story_edit", story_id=story_payload["id"], layout="advanced"))

    assert response.status_code == 200
    assert "Story status" in response.text
    assert "Cybersecurity · Yes" in response.text
    assert "Sentiment · Negative" in response.text


def test_update_news_item_tags_posts_to_news_item_endpoint_and_rerenders_card(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    responses_mock.put(
        f"{Config.TARANIS_CORE_URL}/assess/news-items/news-1/tags",
        json={"message": "Tags updated"},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_payload['id']}",
        json=story_payload,
    )

    response = authenticated_client.post(
        url_for("assess.update_news_item_tags", news_item_id="news-1"),
        data=MultiDict(
            [
                ("story_id", story_payload["id"]),
                ("tags[][name]", "incident"),
                ("tags[][tag_type]", "actor"),
            ]
        ),
    )

    assert response.status_code == 200
    tag_call = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/assess/news-items/news-1/tags"))
    assert json.loads(tag_call.request.body) == [{"name": "incident", "tag_type": "actor"}]
    assert 'id="news-item-card-news-1"' in response.text


def test_update_news_item_tags_filters_blank_rows_before_core_request(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    responses_mock.put(
        f"{Config.TARANIS_CORE_URL}/assess/news-items/news-1/tags",
        json={"message": "Tags updated"},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_payload['id']}",
        json=story_payload,
    )

    response = authenticated_client.post(
        url_for("assess.update_news_item_tags", news_item_id="news-1"),
        data=MultiDict(
            [
                ("story_id", story_payload["id"]),
                ("tags[][name]", ""),
                ("tags[][tag_type]", ""),
            ]
        ),
    )

    assert response.status_code == 200
    tag_call = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/assess/news-items/news-1/tags"))
    assert json.loads(tag_call.request.body) == []


def test_update_news_item_tags_propagates_core_error_and_does_not_rerender_card(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    responses_mock.put(
        f"{Config.TARANIS_CORE_URL}/assess/news-items/news-1/tags",
        status=400,
        json={"message": "Tags not updated"},
    )

    response = authenticated_client.post(
        url_for("assess.update_news_item_tags", news_item_id="news-1"),
        data=MultiDict(
            [
                ("story_id", story_payload["id"]),
                ("tags[][name]", "incident"),
                ("tags[][tag_type]", "actor"),
            ]
        ),
    )

    assert response.status_code == 400
    assert "Tags not updated" in response.text
    assert 'id="news-item-card-news-1"' not in response.text


def test_assess_search_form_uses_single_htmx_submission_path(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": []},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories",
        json={"items": [], "total_count": 0},
    )

    response = authenticated_client.get(url_for("assess.assess", search="pull"))

    assert response.status_code == 200

    tree = html.fromstring(response.text)
    search_form = tree.xpath('//form[@id="assess-search-form"]')[0]
    filter_form = tree.xpath('//form[@id="assess-sidebar"]')[0]
    search_input = tree.xpath('//input[@id="story_search"]')[0]
    clear_button = tree.xpath("//button[@title='Clear time filters']")[0]
    changed_by_select = filter_form.xpath('.//label[.//span[text()="Changed by"]]/select')[0]
    highlight_checkbox = tree.xpath('//input[@name="highlight"]')[0]
    compact_checkbox = tree.xpath('//input[@name="compact_view"]')[0]

    assert search_form.get("hx-trigger") == expected_search_trigger("story_search")
    assert search_form.get("hx-include") == "#assess-sidebar, #selected-tags"
    assert search_form.get("hx-on:submit") == "event.preventDefault()"
    assert filter_form.get("hx-trigger") == "change"
    assert filter_form.get("hx-include") == "#selected-tags"
    assert filter_form.get("hx-on:submit") == "event.preventDefault()"
    assert clear_button.get("hx-include") == "#assess-sidebar, #assess-search-form, #selected-tags"
    assert [option.text for option in changed_by_select.xpath("./option")] == ["Any", "Me"]
    assert highlight_checkbox.get("hx-vals") == "js:{highlight: this.checked}"
    assert compact_checkbox.get("hx-vals") == "js:{compact_view: this.checked}"
    assert search_input.get("hx-get") is None
    assert search_input.get("hx-include") is None
    assert search_input.get("hx-trigger") is None


def test_story_read_action_replaces_story_card(app):
    story = SimpleNamespace(id="1", read=False, important=False, revision_count=0)

    with app.test_request_context():
        markup = render_template_string(
            '{% from "assess/story_actions.html" import story_actions %}{{ story_actions(story) }}',
            story=story,
        )

    tree = html.fromstring(f"<div>{markup}</div>")
    toggle_read = tree.xpath('//*[@data-testid="toggle-read"]')[0]

    assert toggle_read.get("hx-target") == "#story-1"
    assert toggle_read.get("hx-select") == "#story-1"
    assert toggle_read.get("hx-swap") == "outerHTML"


def test_assess_bookmarks_bar_renders_first_six_ordered_collections(authenticated_client, responses_mock):
    story_payload = story_with_news_item_tags()
    bookmark_payloads = [_bookmark_collection_payload(f"bookmark-{index}", f"Bookmark {index}", index, index - 1) for index in range(1, 8)]
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={"tags": [], "sources": [], "groups": [], "languages": []},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories",
        json={"items": [story_payload], "total_count": 1},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/bookmarks",
        json={"items": bookmark_payloads[:6], "total_count": 7},
    )

    response = authenticated_client.get(url_for("assess.assess"))

    assert response.status_code == 200
    tree = html.fromstring(response.text)
    bar = tree.xpath('//*[@data-testid="assess-bookmarks-bar"]')[0]
    assert bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-1"]')
    assert bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-6"]')
    assert not bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-7"]')
    all_bookmarks = bar.xpath('.//*[@data-testid="assess-all-bookmarks"]')[0]
    assert all_bookmarks.get("href") == url_for("assess.bookmarks")
    bookmark_request = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/assess/bookmarks"))
    assert parse_qs(urlparse(bookmark_request.request.url).query) == {"limit": ["6"], "order": ["position_asc"]}


def test_assess_bookmarks_bar_uses_context_limit(app: Any) -> None:
    bookmarks = [SimpleNamespace(id=f"bookmark-{index}", name=f"Bookmark {index}", story_count=index) for index in range(1, 4)]

    with app.test_request_context():
        markup = render_template("assess/bookmarks_bar.html", bookmark_collections=bookmarks, assess_bookmark_bar_limit=2)

    tree = html.fromstring(markup)
    bar = tree.xpath('//*[@data-testid="assess-bookmarks-bar"]')[0]

    assert bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-1"]')
    assert bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-2"]')
    assert not bar.xpath('.//*[@data-testid="assess-bookmark-bookmark-3"]')


def test_filter_token_select_closes_on_outside_click_without_remove_reopen(app):
    with app.test_request_context():
        markup = render_template_string(
            """
            {% from "assess/sidebar/filter_token_select.html" import filter_token_select, filter_token_select_assets %}
            {{ filter_token_select_assets() }}
            {{ filter_token_select(id="source-filter", placeholder="Select sources", selected_items=[], options=[]) }}
            """
        )

    assert '@click.outside="closeList()"' in markup
    assert '@blur="closeList()"' not in markup


def test_source_filter_select_accepts_group_payloads_with_null_key():
    filter_lists = FilterLists(tags=[], sources=[], groups=[{"id": "group-1", "key": None, "name": "Group 1"}], languages=[])

    select_data = StoryView._build_source_filter_select(filter_lists, {"group": ["group-1"]})

    expected_item = {"value": "group-1", "label": "Group 1", "name": "group", "group": "Group"}
    assert expected_item in select_data["options"]
    assert expected_item in select_data["selected_items"]


def test_assess_selection_key_ignores_paging_params():
    selection_key = StoryView._build_assess_selection_key(
        {
            "offset": ["40"],
            "page": ["2"],
            "search": ["incident"],
            "sort": ["date_desc"],
            "tags": ["one", "two"],
        }
    )

    assert selection_key == "search=incident&sort=date_desc&tags=one&tags=two"


def test_assess_redirects_default_saved_filter_into_browser_url(authenticated_client, auth_user, responses_mock):
    saved_user = auth_user.model_copy(deep=True)
    saved_user.profile.assess_saved_filters = [
        AssessSavedFilter(
            id="filter-1",
            name="Shift queue",
            filters={
                "source": ["source-1"],
                "language": ["en"],
                "read": "true",
                "sort": "date_desc",
            },
            is_default=True,
        )
    ]
    add_user_to_cache(saved_user.model_dump(mode="json"))

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/filter-lists",
        json={
            "tags": [],
            "sources": [{"id": "source-1", "name": "Source 1"}],
            "groups": [],
            "languages": ["de", "en"],
        },
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories",
        json={"items": [], "total_count": 0},
    )

    response = authenticated_client.get(url_for("assess.assess"), follow_redirects=False)

    assert response.status_code == 302

    location = urlparse(response.headers["Location"])
    assert location.path == url_for("assess.assess")
    assert parse_qs(location.query) == {
        "source": ["source-1"],
        "language": ["en"],
        "read": ["true"],
        "sort": ["date_desc"],
    }

    followup = authenticated_client.get(url_for("assess.assess"), follow_redirects=True)

    assert followup.status_code == 200

    tree = html.fromstring(followup.text)
    read_select = tree.xpath('//select[@name="read"]')[0]
    source_filter = tree.xpath('//section[@data-filter-id="source-filter"]')[0]
    language_filter = tree.xpath('//section[@data-filter-id="language-filter"]')[0]
    sort_select = tree.xpath('//select[@name="sort"]')[0]

    assert read_select.xpath('./option[@value="true" and @selected]')
    assert source_filter.xpath('.//input[@type="search" and @aria-label="Select sources"]')
    assert "source-1" in source_filter.get("x-data")
    assert '"name": "source"' in source_filter.get("x-data")
    assert language_filter.xpath('.//input[@type="search" and @aria-label="Select languages"]')
    assert '"value": "en"' in language_filter.get("x-data")
    assert '"name": "language"' in language_filter.get("x-data")
    assert sort_select.xpath('./option[@value="date_desc" and @selected]')

    story_request = next(call for call in responses_mock.calls if urlparse(call.request.url).path.endswith("/assess/stories"))
    parsed_query = parse_qs(urlparse(story_request.request.url).query)

    assert parsed_query["source"] == ["source-1"]
    assert parsed_query["language"] == ["en"]
    assert parsed_query["read"] == ["true"]
    assert parsed_query["sort"] == ["date_desc"]


def test_assess_save_saved_filter_posts_selected_filters_to_profile(authenticated_client, responses_mock):
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/users",
        json={
            "id": "user-1",
            "username": "admin",
            "name": "Arthur Dent",
            "profile": {"assess_saved_filters": []},
            "permissions": ["ALL"],
            "roles": [{"id": "role-1", "name": "Admin"}],
        },
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={
            "message": "Profile updated",
            "id": "user-1",
            "user_profile": {"assess_saved_filters": []},
        },
    )

    response = authenticated_client.post(
        url_for("assess.save_saved_filter"),
        data=MultiDict(
            [
                ("name", "Shift queue"),
                ("is_default", "true"),
                ("source", "source-1"),
                ("group", "group-1"),
                ("tags", "alpha"),
                ("tags", "beta"),
                ("language", "en"),
                ("language", "de"),
                ("read", "true"),
                ("important", "false"),
                ("sort", "date_desc"),
                ("range", "week"),
                ("timefrom", "2026-05-01T10:00"),
                ("timeto", "2026-05-02T11:00"),
            ]
        ),
    )

    assert response.status_code == 200
    assert "Assess filter saved." in response.text
    assert "Shift queue" in response.text

    payload = _profile_update_payload(responses_mock)
    assert "assess_default_filters" not in payload
    assert len(payload["assess_saved_filters"]) == 1
    saved_filter = payload["assess_saved_filters"][0]
    assert saved_filter["id"]
    assert UUID(saved_filter["id"]).version == 7
    assert saved_filter == {
        "id": saved_filter["id"],
        "name": "Shift queue",
        "filters": {
            "source": ["source-1"],
            "group": ["group-1"],
            "tags": ["alpha", "beta"],
            "language": ["en", "de"],
            "read": "true",
            "important": "false",
            "sort": "date_desc",
            "range": "week",
            "timefrom": "2026-05-01T10:00",
            "timeto": "2026-05-02T11:00",
        },
        "is_default": True,
    }


def test_assess_save_saved_filter_updates_existing_name(authenticated_client: Any, auth_user: Any, responses_mock: Any) -> None:
    _cache_saved_filters(
        auth_user,
        [
            AssessSavedFilter(id="filter-1", name="Shift queue", filters={"search": "old"}, is_default=False),
        ],
    )
    _mock_profile_update(responses_mock)

    response = authenticated_client.post(
        url_for("assess.save_saved_filter"),
        data=MultiDict([("name", "Shift queue"), ("search", "incident"), ("tags", "alpha"), ("sort", "date_desc")]),
    )

    assert response.status_code == 200
    assert "Assess filter updated." in response.text
    assert _profile_update_payload(responses_mock)["assess_saved_filters"] == [
        {
            "id": "filter-1",
            "name": "Shift queue",
            "filters": {"search": "incident", "tags": ["alpha"], "sort": "date_desc"},
            "is_default": False,
        }
    ]


def test_assess_save_saved_filter_rejects_duplicate_filters(authenticated_client: Any, auth_user: Any, responses_mock: Any) -> None:
    _cache_saved_filters(
        auth_user,
        [
            AssessSavedFilter(id="filter-1", name="Existing", filters={"search": "incident", "tags": ["alpha", "beta"]}, is_default=False),
        ],
    )

    response = authenticated_client.post(
        url_for("assess.save_saved_filter"),
        data=MultiDict([("name", "Different"), ("search", "incident"), ("tags", "beta"), ("tags", "alpha")]),
    )

    assert response.status_code == 400
    assert "These filters are already saved as Existing." in response.text
    assert not any(urlparse(call.request.url).path.endswith("/users/profile") for call in responses_mock.calls)


def test_assess_delete_saved_filter_persists_remaining_filters(authenticated_client: Any, auth_user: Any, responses_mock: Any) -> None:
    _cache_saved_filters(
        auth_user,
        [
            AssessSavedFilter(id="filter-1", name="Old default", filters={"search": "old"}, is_default=True),
            AssessSavedFilter(id="filter-2", name="Keep", filters={"search": "keep"}, is_default=False),
        ],
    )
    _mock_profile_update(responses_mock)

    with authenticated_client.session_transaction() as session:
        session[ASSESS_SAVED_FILTER_SESSION_KEY] = True

    response = authenticated_client.delete(url_for("assess.delete_saved_filter", filter_id="filter-1"))

    assert response.status_code == 200
    assert "Assess filter deleted." in response.text
    assert "Old default" not in response.text
    assert "Keep" in response.text
    assert _profile_update_payload(responses_mock)["assess_saved_filters"] == [
        {"id": "filter-2", "name": "Keep", "filters": {"search": "keep"}, "is_default": False}
    ]

    with authenticated_client.session_transaction() as session:
        assert session[ASSESS_SAVED_FILTER_SESSION_KEY] is False


def test_assess_set_saved_filter_default_does_not_update_session_on_profile_error(authenticated_client, auth_user, responses_mock):
    _cache_saved_filters(
        auth_user,
        [
            AssessSavedFilter(id="filter-1", name="Shift queue", filters={"search": "old"}, is_default=False),
        ],
    )
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/users/profile",
        json={"error": "Profile update failed"},
        status=400,
    )

    with authenticated_client.session_transaction() as session:
        session[ASSESS_SAVED_FILTER_SESSION_KEY] = True

    response = authenticated_client.post(url_for("assess.set_saved_filter_default", filter_id="filter-1"))

    assert response.status_code == 400

    with authenticated_client.session_transaction() as session:
        assert session[ASSESS_SAVED_FILTER_SESSION_KEY] is True


def test_assess_saved_filters_dialog_uses_submit_button(authenticated_client):
    response = authenticated_client.get(url_for("assess.saved_filters"))
    tree = html.fromstring(response.text)

    form = tree.xpath('//form[@id="saved-filter-form"]')[0]
    button = form.xpath('.//button[@type="submit"]')[0]
    disabled_reason = tree.xpath('//*[@id="saved-filter-disabled-reason"]')[0]

    assert form.get("method") == "post"
    assert form.get("action") == url_for("assess.save_saved_filter")
    assert form.get("hx-target-error") == "#assess_saved_filters_dialog"
    assert button.get("type") == "submit"
    assert button.get("disabled") == "disabled"
    assert button.get("aria-describedby") == "saved-filter-disabled-reason"
    assert disabled_reason.text_content() == "Apply at least one Assess filter before saving."


def test_assess_saved_filter_update_button_reuses_save_endpoint(authenticated_client: Any, auth_user: Any) -> None:
    _cache_saved_filters(
        auth_user,
        [
            AssessSavedFilter(id="filter-1", name="Shift queue", filters={"search": "old"}, is_default=False),
        ],
    )

    response = authenticated_client.get(url_for("assess.saved_filters", search="incident"))
    tree = html.fromstring(response.text)
    update_button = tree.xpath('//button[normalize-space()="Update"]')[0]
    update_values = update_button.get("hx-vals")

    assert update_button.get("hx-post") == url_for("assess.save_saved_filter")
    assert update_values is not None
    assert json.loads(update_values) == {"name": "Shift queue"}
    assert update_button.get("disabled") is None


def test_table_search_bar_uses_form_level_search_trigger(app):
    with app.test_request_context("/frontend/admin/osint-sources?search=alpha"):
        markup = render_template_string(
            '{% from "macros/table.html" import table_search_bar %}{{ table_search_bar("osint_table", "/frontend/admin/osint-sources") }}'
        )

    tree = html.fromstring(markup)
    form = tree.xpath("//form")[0]
    search_input = tree.xpath('//input[@id="osint_table-search"]')[0]

    assert form.get("hx-trigger") == expected_search_trigger("osint_table-search")
    assert form.get("hx-on:submit") == "event.preventDefault()"
    assert search_input.get("hx-trigger") is None


def test_create_news_item_from_url_posts_simple_web_collector_payload(authenticated_client, responses_mock):
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/assess/news-items/fetch",
        json={"story_ids": ["story-1"], "news_item_ids": ["news-1"], "message": "1 News items added successfully"},
    )

    response = authenticated_client.post(
        url_for("assess.create_news_item"),
        data={
            "fetch_url": "https://example.com/story",
            "parameters[XPATH]": "//article",
            "parameters[TLP_LEVEL]": "green",
            "parameters[BROWSER_MODE]": "true",
            "parameters[DIGEST_SPLITTING]": "false",
            "parameters[DIGEST_SPLITTING_LIMIT]": "30",
        },
    )

    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == url_for("assess.story_edit", story_id="story-1")
    assert responses_mock.calls[0].request.url == f"{Config.TARANIS_CORE_URL}/assess/news-items/fetch"
    assert responses_mock.calls[0].request.body
    assert json.loads(responses_mock.calls[0].request.body) == {
        "id": "manual",
        "type": "simple_web_collector",
        "parameters": {
            "WEB_URL": "https://example.com/story",
            "XPATH": "//article",
            "TLP_LEVEL": "green",
            "BROWSER_MODE": "true",
            "DIGEST_SPLITTING": "false",
            "DIGEST_SPLITTING_LIMIT": "30",
        },
    }


def test_story_sharing_dialog_loads_connectors_from_assess_endpoint(authenticated_client_basic, responses_mock):
    story_id = "story-1"
    connector_id = "connector-1"

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}",
        json={"id": story_id, "title": "Shared Story", "links": ["https://example.com/story"]},
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/connectors",
        json={
            "total_count": 1,
            "items": [
                {
                    "id": connector_id,
                    "name": "MISP Connector",
                    "description": "User-visible connector",
                    "type": "misp_connector",
                }
            ],
        },
    )

    response = authenticated_client_basic.get(url_for("assess.share_story", story_id=story_id))

    assert response.status_code == 200
    assert connector_id in response.text
    assert "MISP Connector" in response.text
    assert all(call.request.url != f"{Config.TARANIS_CORE_URL}/config/connectors" for call in responses_mock.calls)


def test_story_sharing_dialog_still_renders_when_connector_loading_fails(authenticated_client_basic, monkeypatch, responses_mock):
    story_id = "story-1"

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}",
        json={"id": story_id, "title": "Shared Story", "links": ["https://example.com/story"]},
    )

    def raise_connector_loading_error(*args, **kwargs):
        raise RuntimeError("permission lookup failed")

    monkeypatch.setattr("frontend.views.story_views.DataPersistenceLayer.get_objects", raise_connector_loading_error)

    response = authenticated_client_basic.get(url_for("assess.share_story", story_id=story_id))

    assert response.status_code == 200
    assert "Share Stories" in response.text
    assert "Shared Story" not in response.text
    assert "Connector sharing is not available for your account" in response.text
    assert "Share via email" in response.text
    assert "Export to JSON" in response.text

    tree = html.fromstring(response.text)
    connector_select = tree.xpath('//select[@id="connector"]')
    assert len(connector_select) == 0


def test_story_sharing_dialog_still_renders_when_connector_loading_is_forbidden(authenticated_client_basic, monkeypatch, responses_mock):
    story_id = "story-1"

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}",
        json={"id": story_id, "title": "Shared Story", "links": ["https://example.com/story"]},
    )

    def raise_connector_loading_error(*args, **kwargs):
        raise Forbidden("connector access denied")

    monkeypatch.setattr("frontend.views.story_views.DataPersistenceLayer.get_objects", raise_connector_loading_error)

    response = authenticated_client_basic.get(url_for("assess.share_story", story_id=story_id))

    assert response.status_code == 200
    assert "Share Stories" in response.text
    assert "Connector sharing is not available for your account" in response.text
    assert "Share via email" in response.text
    assert "Export to JSON" in response.text

    tree = html.fromstring(response.text)
    connector_select = tree.xpath('//select[@id="connector"]')
    assert len(connector_select) == 0


def test_handle_news_item_response_returns_notification_and_content(app, monkeypatch):
    monkeypatch.setattr(StoryView, "get_notification_from_response", lambda response, oob=True: "notification")

    response = SimpleNamespace(ok=True, json=lambda: {"story_id": "story-1"})

    with app.test_request_context("/"):
        result = StoryView._handle_news_item_response(
            response,
            content_builder=lambda _story_id: "<div>content</div>",
            redirect_on_story=False,
        )

    assert result.status_code == 200  # type: ignore
    assert result.get_data(as_text=True) == "notification<div>content</div>"  # type: ignore
