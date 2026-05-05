import json
from types import SimpleNamespace

from flask import render_template_string, url_for
from lxml import html
from werkzeug.exceptions import Forbidden

from frontend.config import Config
from frontend.views.story_views import StoryView, _calculate_story_diff, _normalize_story_import_payload


def test_calculate_story_diff_ignores_empty_tag_changes():
    from_data = {
        "title": "Story title",
        "tags": [{"name": None}],
    }
    to_data = {
        "title": "Story title",
        "tags": [{"name": ""}, {"name": "   "}],
    }

    changes = _calculate_story_diff(from_data, to_data)

    assert changes == []


def test_calculate_story_diff_keeps_real_tag_changes():
    from_data = {
        "title": "Story title",
        "tags": [{"name": None}, {"name": "existing"}],
    }
    to_data = {
        "title": "Story title",
        "tags": [{"name": ""}, {"name": "existing"}, {"name": "new-tag"}],
    }

    changes = _calculate_story_diff(from_data, to_data)

    assert {"field": "Tags Added", "old_value": None, "new_value": "new-tag"} in changes


def test_calculate_story_diff_uses_inline_markup_for_text_changes():
    from_data = {"title": "Kill Chain im Krieg verkurzt"}
    to_data = {"title": "Kill Chain im Krieg deutlich verkurzt"}

    changes = _calculate_story_diff(from_data, to_data)

    assert len(changes) == 1
    assert changes[0]["field"] == "Title"
    assert changes[0]["inline_diff"] is True
    assert "bg-success/20" in str(changes[0]["new_value_diff"])
    assert "deutlich " in str(changes[0]["new_value_diff"])
    assert "deutlich " not in str(changes[0]["old_value_diff"])


def test_calculate_story_diff_escapes_inline_markup_text():
    from_data = {"title": "A <script>alert(1)</script> title"}
    to_data = {"title": "A <script>alert(1)</script> new title"}

    changes = _calculate_story_diff(from_data, to_data)

    assert len(changes) == 1
    assert "&lt;script&gt;" in str(changes[0]["new_value_diff"])
    assert "<script>" not in str(changes[0]["new_value_diff"])


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
            "news_items": [
                {
                    "id": "news-1",
                    "title": "Imported Story News 1",
                    "source": "https://example.com/source",
                    "content": "content",
                    "osint_source_id": "99",
                    "story_id": "story-1",
                }
            ],
        }
    ]


def test_manual_news_item_form_routes_htmx_errors_to_notification_bar(authenticated_client):
    response = authenticated_client.get(url_for("assess.get_news_item", news_item_id=0))

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

    assert search_form.get("hx-trigger") == "input changed delay:500ms from:#story_search, search from:#story_search"
    assert search_form.get("hx-include") == "#assess-sidebar, #selected-tags"
    assert search_form.get("hx-on:submit") == "event.preventDefault()"
    assert filter_form.get("hx-trigger") == "change"
    assert filter_form.get("hx-include") == "#selected-tags"
    assert filter_form.get("hx-on:submit") == "event.preventDefault()"
    assert search_input.get("hx-get") is None
    assert search_input.get("hx-include") is None
    assert search_input.get("hx-trigger") is None


def test_table_search_bar_uses_form_level_search_trigger(app):
    with app.test_request_context("/frontend/admin/osint-sources?search=alpha"):
        markup = render_template_string(
            '{% from "macros/table.html" import table_search_bar %}{{ table_search_bar("osint_table", "/frontend/admin/osint-sources") }}'
        )

    tree = html.fromstring(markup)
    form = tree.xpath("//form")[0]
    search_input = tree.xpath('//input[@id="osint_table-search"]')[0]

    assert form.get("hx-trigger") == "input changed delay:500ms from:#osint_table-search, search from:#osint_table-search"
    assert form.get("hx-on:submit") == "event.preventDefault()"
    assert search_input.get("hx-trigger") is None


def test_omnisearch_dialog_form_uses_htmx_submit(authenticated_client):
    response = authenticated_client.get(url_for("base.omnisearch"))

    assert response.status_code == 200

    tree = html.fromstring(response.text)
    form = tree.xpath('//dialog[@id="assess_search_dialog"]//div[@class="modal-box"]/form')[0]
    search_input = tree.xpath('//input[@id="omni_search"]')[0]

    assert form.get("hx-trigger") == "input changed delay:500ms from:#omni_search, search from:#omni_search"
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

    tree = html.fromstring(response.text)
    connector_select = tree.xpath('//select[@id="connector"]')
    assert len(connector_select) == 1
    options = connector_select[0].xpath("./option")
    assert len(options) == 1
    assert options[0].text == "Select a connector"


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

    tree = html.fromstring(response.text)
    connector_select = tree.xpath('//select[@id="connector"]')
    assert len(connector_select) == 1
    options = connector_select[0].xpath("./option")
    assert len(options) == 1
    assert options[0].text == "Select a connector"


def test_handle_news_item_response_returns_notification_and_content(app, monkeypatch):
    monkeypatch.setattr(StoryView, "get_notification_from_response", lambda response, oob=True: "notification")

    response = SimpleNamespace(ok=True, json=lambda: {"story_id": "story-1"})

    with app.test_request_context("/"):
        result = StoryView._handle_news_item_response(
            response,
            content_builder=lambda _story_id: "<div>content</div>",
            redirect_on_story=False,
        )

    assert result.status_code == 200
    assert result.get_data(as_text=True) == "notification<div>content</div>"
