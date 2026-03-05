import pytest
from flask import url_for
from lxml import html

from frontend.views.admin_views.bot_views import BotView


@pytest.mark.parametrize(
    "bot_type",
    [
        "nlp_bot",
        "story_bot",
        "summary_bot",
        "sentiment_analysis_bot",
        "cybersec_classifier_bot",
    ],
)
def test_bot_parameters_include_optional_positive_integer_requests_timeout(authenticated_client, htmx_header, bot_type):
    response = authenticated_client.get(
        url_for("admin.bot_parameters", bot_id="0", type=bot_type),
        headers=htmx_header,
    )
    assert response.status_code == 200

    tree = html.fromstring(response.text)
    requests_timeout_fields = tree.xpath('//input[@name="parameters[REQUESTS_TIMEOUT]"]')
    item_filter_fields = tree.xpath('//input[@name="parameters[ITEM_FILTER]"]')
    assert len(requests_timeout_fields) == 1
    assert len(item_filter_fields) == 1
    assert requests_timeout_fields[0].get("type") == "text"
    assert requests_timeout_fields[0].get("pattern") == "^[1-9][0-9]*$"
    assert requests_timeout_fields[0].get("required") is None
    assert response.text.index('name="parameters[ITEM_FILTER]"') < response.text.index('name="parameters[REQUESTS_TIMEOUT]"')


def test_reorder_bot_parameters_uses_bot_specific_order_and_keeps_unknowns_stable():
    parameters = [
        {"name": "REFRESH_INTERVAL"},
        {"name": "UNKNOWN_ONE"},
        {"name": "BOT_API_KEY"},
        {"name": "ITEM_FILTER"},
        {"name": "UNKNOWN_TWO"},
        {"name": "REQUESTS_TIMEOUT"},
    ]

    ordered = BotView._reorder_bot_parameters("story_bot", parameters)

    assert [param["name"] for param in ordered] == [
        "ITEM_FILTER",
        "REQUESTS_TIMEOUT",
        "BOT_API_KEY",
        "REFRESH_INTERVAL",
        "UNKNOWN_ONE",
        "UNKNOWN_TWO",
    ]


def test_reorder_bot_parameters_returns_original_order_for_unknown_bot_type():
    parameters = [{"name": "B"}, {"name": "A"}, {"name": "C"}]

    ordered = BotView._reorder_bot_parameters("unknown_bot_type", parameters)

    assert [param["name"] for param in ordered] == [
        "B",
        "A",
        "C",
    ]
