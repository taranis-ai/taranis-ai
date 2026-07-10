from types import SimpleNamespace
from typing import Any

import pytest
from flask import render_template, url_for
from lxml import html
from models.admin import Bot
from models.types import BOT_TYPES

from frontend.views.admin_views.bot_views import BotView


pytestmark = pytest.mark.usefixtures("mock_worker_parameters_get")


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
    refresh_interval_fields = tree.xpath('//input[@name="parameters[REFRESH_INTERVAL]"]')
    assert len(requests_timeout_fields) == 1
    assert len(item_filter_fields) == 1
    assert len(refresh_interval_fields) == 1
    assert requests_timeout_fields[0].get("type") == "text"
    assert requests_timeout_fields[0].get("pattern") == "^[1-9][0-9]*$"
    assert requests_timeout_fields[0].get("required") is None
    assert refresh_interval_fields[0].get("required") is None
    assert response.text.index('name="parameters[ITEM_FILTER]"') < response.text.index('name="parameters[REQUESTS_TIMEOUT]"')


def test_summary_bot_parameters_include_split_summary_and_title_endpoints(authenticated_client, htmx_header):
    response = authenticated_client.get(
        url_for("admin.bot_parameters", bot_id="0", type="summary_bot"),
        headers=htmx_header,
    )
    assert response.status_code == 200

    tree = html.fromstring(response.text)
    summary_endpoint_fields = tree.xpath('//input[@name="parameters[SUMMARY_ENDPOINT]"]')
    title_endpoint_fields = tree.xpath('//input[@name="parameters[TITLE_ENDPOINT]"]')

    assert len(summary_endpoint_fields) == 1
    assert len(title_endpoint_fields) == 1
    assert summary_endpoint_fields[0].get("required") is None
    assert title_endpoint_fields[0].get("required") is None

    # Ensure ordering matches Worker._order_parameters: BOT_API_KEY, SUMMARY_ENDPOINT,
    # TITLE_ENDPOINT, RUN_AFTER_COLLECTOR
    bot_api_key_index = response.text.index('name="parameters[BOT_API_KEY]"')
    summary_endpoint_index = response.text.index('name="parameters[SUMMARY_ENDPOINT]"')
    title_endpoint_index = response.text.index('name="parameters[TITLE_ENDPOINT]"')
    run_after_collector_index = response.text.index('name="parameters[RUN_AFTER_COLLECTOR]"')

    assert bot_api_key_index < summary_endpoint_index
    assert summary_endpoint_index < title_endpoint_index
    assert title_endpoint_index < run_after_collector_index


def test_bot_menu_badge_uses_task_failure_count(monkeypatch):
    fake_badges = SimpleNamespace(bot=7)
    monkeypatch.setattr(
        "frontend.views.admin_views.bot_views.DataPersistenceLayer",
        lambda: SimpleNamespace(get_object=lambda model: fake_badges),
    )

    assert BotView.get_admin_menu_badge() == 7


def test_bot_form_renders_enabled_switch(app):
    bot = Bot.model_construct(
        id="42",
        name="Test bot",
        description="",
        type=BOT_TYPES.NLP_BOT,
        index=1,
        enabled=False,
        parameters={},
        status=None,
    )

    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_form.html",
            bot=bot,
            submit_text="Update Bot",
            form_action='hx-put="/frontend/admin/bots/42"',
            bot_types=[],
            parameters=[],
            parameter_values={},
        )

    tree = html.fromstring(rendered)
    enabled_fields = tree.xpath('//input[@name="enabled"]')

    assert len(enabled_fields) == 2
    assert tree.xpath('//input[@name="enabled"][@type="hidden"][@value="false"]')
    assert tree.xpath('//input[@name="enabled"][@type="checkbox"][@value="true"]')


def test_bot_context_handles_missing_parameters(app: Any, monkeypatch: pytest.MonkeyPatch):
    bot = Bot.model_construct(
        id="42",
        name="Test bot",
        description="",
        type=BOT_TYPES.NLP_BOT,
        index=1,
        enabled=True,
        parameters=None,
        status=None,
    )
    monkeypatch.setattr(BotView, "get_worker_parameters", classmethod(lambda cls, worker_type: []))
    monkeypatch.setattr(BotView, "get_bot_type_options", classmethod(lambda cls, current_bot=None: []))
    monkeypatch.setattr(BotView, "get_run_after_options", classmethod(lambda cls, current_type="": []))
    monkeypatch.setattr(
        BotView,
        "get_dag_preview",
        classmethod(lambda cls, bot_id, payload: {"order": [], "edges": [], "nodes": [], "warnings": []}),
    )

    with app.test_request_context("/"):
        context = BotView.get_extra_context({"bot": bot, "bot_id": bot.id})

    assert context["parameter_values"] == {}
    assert context["selected_run_after"] == []


def test_run_after_options_exclude_current_bot_type(monkeypatch):
    fake_bots = SimpleNamespace(
        items=[
            SimpleNamespace(type=BOT_TYPES.IOC_BOT, name="IOC Bot", enabled=True),
            SimpleNamespace(type=BOT_TYPES.NLP_BOT, name="NLP Bot", enabled=True),
        ]
    )
    monkeypatch.setattr(
        "frontend.views.admin_views.bot_views.DataPersistenceLayer",
        lambda: SimpleNamespace(get_objects=lambda model: fake_bots),
    )

    options = BotView.get_run_after_options("ioc_bot")

    assert options == [{"id": "NLP_BOT", "name": "NLP Bot (NLP_BOT)", "enabled": "true"}]


def test_bot_run_order_controls_render_selected_dependencies(app):
    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_run_order.html",
            bot_id="bot-1",
            parameter_values={"RUN_AFTER_COLLECTOR": "true", "RUN_AFTER_BOTS": "IOC_BOT"},
            selected_run_after=["IOC_BOT"],
            run_after_options=[{"id": "IOC_BOT", "name": "IOC Bot (IOC_BOT)", "enabled": "true"}],
            dag_preview={"order": [], "edges": [], "warnings": []},
        )

    tree = html.fromstring(rendered)
    assert tree.xpath('//input[@name="parameters[RUN_AFTER_COLLECTOR]"][@type="checkbox"][@checked]')
    selected_options = tree.xpath('//select[@id="run-after-bots-select"]/option[@value="IOC_BOT"][@selected]')
    assert len(selected_options) == 1
    assert "DOMContentLoaded" in rendered


def test_bot_dag_preview_renders_warnings(app):
    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_dag_preview.html",
            bot_id="bot-1",
            dag_preview={"order": [], "edges": [], "warnings": ["Bot run order contains a cycle"]},
        )

    assert "Bot run order contains a cycle" in rendered


def test_bot_dag_preview_uses_submitted_collector_toggle(
    authenticated_client: Any, htmx_header: dict[str, str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        BotView,
        "get_dag_preview",
        classmethod(lambda cls, bot_id, payload: {"order": [{"name": "Wordlist Bot"}], "edges": [], "warnings": []}),
    )

    response = authenticated_client.post(
        url_for("admin.bot_dag_preview", bot_id="0"),
        data={"parameters[RUN_AFTER_COLLECTOR]": "true"},
        headers=htmx_header,
    )

    assert response.status_code == 200
    assert "Collector Chain" in response.text
    assert "Wordlist Bot" in response.text


def test_bot_dag_preview_hides_collector_chain_without_collector_root(app: Any):
    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_dag_preview.html",
            bot_id="bot-1",
            run_after_collector=False,
            dag_preview={"order": [{"name": "Wordlist Bot"}], "edges": [], "warnings": []},
        )

    assert "Collector Chain" not in rendered
    assert "Wordlist Bot" not in rendered


def test_bot_dag_preview_shows_collector_chain_for_collector_root(app: Any):
    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_dag_preview.html",
            bot_id="bot-1",
            run_after_collector=True,
            dag_preview={"order": [{"name": "Wordlist Bot"}], "edges": [], "warnings": []},
        )

    assert "Collector Chain" in rendered
    assert "Wordlist Bot" in rendered
