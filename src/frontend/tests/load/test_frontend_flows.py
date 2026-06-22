from __future__ import annotations

import pytest
from tests.load.load_support.browser_flows import build_selected_e2e_flow_user_class, parse_selected_flow_names
from tests.load.load_testing.frontend_flows import (
    FLOW_ANALYZE_LIST,
    FLOW_ASSESS_LIST,
    FLOW_DASHBOARD,
    FLOW_LOGIN,
    LOAD_MEASURED_FLOW_ATTR,
    get_flow_definition,
    get_load_enabled_flows,
    load_measured_flow,
)


def test_parse_selected_flow_names_trims_and_preserves_order() -> None:
    assert parse_selected_flow_names(" login, dashboard ,assess_list ") == [
        FLOW_LOGIN,
        FLOW_DASHBOARD,
        FLOW_ASSESS_LIST,
    ]


def test_parse_selected_flow_names_treats_empty_string_as_default() -> None:
    assert parse_selected_flow_names("") is None


def test_parse_selected_flow_names_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="no valid flow names"):
        parse_selected_flow_names(" , ")


def test_get_load_enabled_flows_can_filter_by_name() -> None:
    filtered = get_load_enabled_flows([FLOW_LOGIN, FLOW_ANALYZE_LIST])
    assert [flow.name for flow in filtered] == [FLOW_LOGIN, FLOW_ANALYZE_LIST]


def test_flow_definition_contains_expected_page_event_name() -> None:
    assert get_flow_definition(FLOW_DASHBOARD).page_event_name == "dashboard:ready"


def test_load_measured_flow_decorator_records_flow_names() -> None:
    @load_measured_flow(FLOW_LOGIN, FLOW_ASSESS_LIST)
    def wrapper():
        return None

    assert getattr(wrapper, LOAD_MEASURED_FLOW_ATTR) == (FLOW_LOGIN, FLOW_ASSESS_LIST)


def test_generated_flow_tasks_keep_flow_specific_inner_names() -> None:
    user_class = build_selected_e2e_flow_user_class()

    wrapped_task = getattr(user_class, f"{FLOW_DASHBOARD}_flow")
    sync_wrapped_task = wrapped_task.__closure__[0].cell_contents
    measured_task = sync_wrapped_task.__closure__[0].cell_contents

    assert measured_task.__name__ == f"{FLOW_DASHBOARD}_flow"
