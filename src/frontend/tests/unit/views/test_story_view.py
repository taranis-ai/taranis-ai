from flask import url_for
from lxml import html

from frontend.views.story_views import _calculate_story_diff, _normalize_story_import_payload


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
