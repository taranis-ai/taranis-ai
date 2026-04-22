from types import SimpleNamespace

from flask import url_for
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

    assert len(form) == 1
    assert form[0].get("hx-target-error") == "#notification-bar"
    assert len(file_form) == 1
    assert file_form[0].get("hx-target-error") == "#notification-bar"

    source_input = form[0].xpath('.//input[@name="source"]')
    assert len(source_input) == 1
    assert source_input[0].get("required") is None


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
