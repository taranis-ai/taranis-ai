import json
from types import SimpleNamespace

import pytest
from flask import Flask, render_template, url_for
from lxml import html
from models.admin import Bot
from models.types import BOT_TYPES

from frontend.views.admin_views.admin_base_view import AdminBaseView
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
    refresh_interval_fields = tree.xpath('//input[@name="parameters[REFRESH_INTERVAL]"]')
    assert len(requests_timeout_fields) == 1
    assert len(item_filter_fields) == 1
    assert len(refresh_interval_fields) == 1
    assert requests_timeout_fields[0].get("type") == "number"
    assert requests_timeout_fields[0].get("min") == "1"
    assert requests_timeout_fields[0].get("required") is None
    assert refresh_interval_fields[0].get("required") is None
    assert tree.xpath('//*[@title="LLM request timeout in seconds."]')
    assert response.text.index('name="parameters[ITEM_FILTER]"') < response.text.index('name="parameters[REQUESTS_TIMEOUT]"')


def test_worker_parameter_numeric_upper_bounds(monkeypatch):
    monkeypatch.setattr(
        "frontend.views.admin_views.admin_base_view.parameter_schema",
        lambda _worker_type: {
            "properties": {
                "ZERO_MAX": {"type": "integer", "maximum": 0},
                "EXCLUSIVE_INT_MAX": {"type": "integer", "exclusiveMaximum": 5},
                "EXCLUSIVE_NUMBER_MAX": {"type": "number", "exclusiveMaximum": 5.5},
            }
        },
    )

    fields = {field["name"]: field for field in AdminBaseView.get_worker_parameters("test")}

    assert fields["ZERO_MAX"]["maximum"] == 0
    assert fields["EXCLUSIVE_INT_MAX"]["maximum"] == 4
    assert fields["EXCLUSIVE_NUMBER_MAX"]["maximum"] is None


def test_worker_parameter_form_renders_native_boolean_and_object_values(app):
    with app.test_request_context("/"):
        rendered = render_template(
            "partials/worker_parameters.html",
            parameters=AdminBaseView.get_worker_parameters("RSS_COLLECTOR"),
            parameter_values={
                "FEED_URL": "https://example.test/feed",
                "USE_GLOBAL_PROXY": True,
                "ADDITIONAL_HEADERS": {"X-Test": "1"},
            },
        )

    tree = html.fromstring(rendered)
    assert tree.xpath('//input[@name="parameters[USE_GLOBAL_PROXY]"][@type="checkbox"][@checked]')
    headers = tree.xpath('//textarea[@name="parameters[ADDITIONAL_HEADERS]"]')[0]
    assert json.loads(headers.text) == {"X-Test": "1"}


def test_worker_parameter_form_groups_required_and_optional_settings(app):
    with app.test_request_context("/"):
        rendered = render_template(
            "partials/worker_parameters.html",
            parameters=AdminBaseView.get_worker_parameters("RSS_COLLECTOR"),
            parameter_values={"FEED_URL": "https://example.test/feed", "USER_AGENT": "Taranis", "CONTENT_LOCATION": "article"},
        )

    tree = html.fromstring(rendered)
    required = tree.xpath('//*[@data-testid="required-worker-parameters"]')[0]
    optional = tree.xpath('//details[@data-testid="optional-worker-parameters"]')[0]

    assert required.xpath('.//*[@data-parameter="FEED_URL"]')
    assert not required.xpath('.//*[@data-parameter="USER_AGENT"]')
    assert optional.xpath('.//*[@data-parameter="USER_AGENT"]')
    assert optional.get("open") is None
    assert "12 available" in optional.text_content()
    assert "2 configured" in optional.text_content()
    assert "md:col-span-2" in optional.xpath('.//*[@data-parameter="ADDITIONAL_HEADERS"]')[0].get("class", "")


def test_worker_parameter_form_handles_workers_without_required_or_additional_settings(app):
    with app.test_request_context("/"):
        optional_only = render_template(
            "partials/worker_parameters.html",
            parameters=AdminBaseView.get_worker_parameters("ANALYST_BOT"),
            parameter_values={},
        )
        empty = render_template(
            "partials/worker_parameters.html",
            parameters=[],
            worker_parameters_selected=True,
        )

    optional_tree = html.fromstring(optional_only)
    assert not optional_tree.xpath('//*[@data-testid="required-worker-parameters"]')
    assert optional_tree.xpath('//details[@data-testid="optional-worker-parameters"]')
    assert "No required settings" in optional_tree.text_content()

    empty_tree = html.fromstring(empty)
    assert empty_tree.xpath('//*[@data-testid="worker-parameter-empty-state"]')
    assert "No additional worker configuration is required" in empty_tree.text_content()


def test_worker_parameter_form_groups_template_selector_with_required_settings(app):
    with app.test_request_context("/"):
        rendered = render_template(
            "product_type/product_type_parameters.html",
            parameters=AdminBaseView.get_worker_parameters("PANDOC_PRESENTER"),
            parameter_values={},
            template_options=[{"id": "report.html", "name": "Report"}],
            worker_parameters_selected=True,
        )

    tree = html.fromstring(rendered)
    required = tree.xpath('//*[@data-testid="required-worker-parameters"]')[0]
    template_select = required.xpath('.//select[@name="parameters[TEMPLATE_PATH]"]')
    assert len(template_select) == 1
    assert template_select[0].get("required") is not None
    assert template_select[0].xpath('./option[@value="report.html"]')


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

    # Field order comes directly from the shared Pydantic parameter model.
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


def test_bot_form_renders_state_buttons_and_run_action(app):
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
    assert tree.xpath('//input[@name="id"][@type="hidden"][@value="42"]')
    assert not tree.xpath('//input[@name="enabled"]')
    enabled_buttons = tree.xpath('//button[@hx-post="/frontend/admin/toggle_bot_state/42/enabled"][normalize-space()="Enabled"]')
    disabled_buttons = tree.xpath('//button[@hx-post="/frontend/admin/toggle_bot_state/42/disabled"][normalize-space()="Disabled"]')
    assert enabled_buttons
    assert disabled_buttons
    assert enabled_buttons[0].get("hx-swap") == "outerHTML"
    assert disabled_buttons[0].get("hx-swap") == "outerHTML"
    run_buttons = tree.xpath('//button[contains(@hx-post, "/bot_execute/42")][normalize-space()="Run"]')
    assert len(run_buttons) == 1


def test_bot_create_form_omits_sentinel_id(app: Flask):
    bot = Bot.model_construct(id="0", name="", description="", type=None, index=None, enabled=True, parameters={}, status=None)

    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_form.html",
            bot=bot,
            submit_text="Create Bot",
            form_action="/frontend/admin/bots",
            bot_types=BotView.bot_types.values(),
            parameters=[],
            parameter_values={},
        )

    assert not html.fromstring(rendered).xpath('//input[@name="id"]')


def test_run_after_options_use_bot_instance_ids_and_allow_duplicate_types(monkeypatch: pytest.MonkeyPatch):
    first_id = "019f4bc8-a467-7216-a2d8-731869323507"
    second_id = "019f4bc8-a467-7216-a2d8-7319fae631e2"
    bots = [
        Bot.model_construct(id=first_id, name="IOC Europe", type=BOT_TYPES.IOC_BOT, enabled=True),
        Bot.model_construct(id=second_id, name="IOC Americas", type=BOT_TYPES.IOC_BOT, enabled=True),
    ]
    monkeypatch.setattr(
        "frontend.views.admin_views.bot_views.DataPersistenceLayer",
        lambda: SimpleNamespace(get_objects=lambda model: SimpleNamespace(items=bots)),
    )

    assert BotView.get_run_after_options(first_id) == [{"id": second_id, "name": "IOC Americas (IOC_BOT)", "enabled": "true"}]


def test_bot_run_order_controls_render_selected_dependencies(app):
    ioc_bot_id = "019f4bc8-a467-7216-a2d8-7319fae631e2"
    with app.test_request_context("/"):
        rendered = render_template(
            "bot/bot_run_order.html",
            bot_id="bot-1",
            parameter_values={"RUN_AFTER_COLLECTOR": True, "RUN_AFTER_BOTS": [ioc_bot_id]},
            selected_run_after=[ioc_bot_id],
            run_after_options=[{"id": ioc_bot_id, "name": "IOC Bot (IOC_BOT)", "enabled": "true"}],
            dag_preview={"order": [{"name": "Wordlist Bot"}, {"name": "IOC Bot"}], "edges": [], "warnings": []},
        )

    tree = html.fromstring(rendered)
    assert tree.xpath('//input[@name="parameters[RUN_AFTER_COLLECTOR]"][@type="checkbox"][@checked]')
    selected_options = tree.xpath(f'//select[@id="run-after-bots-select"]/option[@value="{ioc_bot_id}"][@selected]')
    assert len(selected_options) == 1
    preview_include = tree.xpath('//div[@id="bot-dag-preview"]')[0].get("hx-include")
    assert preview_include is not None
    assert "[name='name']" not in preview_include
    assert "[name='description']" not in preview_include
    assert "[name='id']" in preview_include
    assert "[name='parameters[RUN_AFTER_COLLECTOR]']" in preview_include
    assert "[name='parameters[RUN_AFTER_BOTS][]']" in preview_include
    assert tree.xpath('//div[@id="bot-dag-preview"]')[0].get("hx-post") == url_for("admin.bot_dag_preview")
    assert "Collector Chain" in rendered
    assert "Wordlist Bot" in rendered
    assert "IOC Bot" in rendered
    assert "DOMContentLoaded" in rendered
