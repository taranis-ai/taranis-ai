from __future__ import annotations

import unittest

from load_support.browser_flows import parse_selected_flow_names
from testsupport.load_testing.frontend_flows import (
    FLOW_ANALYZE_LIST,
    FLOW_ASSESS_LIST,
    FLOW_DASHBOARD,
    FLOW_LOGIN,
    LOAD_MEASURED_FLOW_ATTR,
    get_flow_definition,
    get_load_enabled_flows,
    load_measured_flow,
)


class FrontendFlowsTest(unittest.TestCase):
    def test_parse_selected_flow_names_trims_and_preserves_order(self) -> None:
        self.assertEqual(
            parse_selected_flow_names(" login, dashboard ,assess_list "),
            [FLOW_LOGIN, FLOW_DASHBOARD, FLOW_ASSESS_LIST],
        )

    def test_parse_selected_flow_names_treats_empty_string_as_default(self) -> None:
        self.assertIsNone(parse_selected_flow_names(""))

    def test_parse_selected_flow_names_rejects_empty_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "no valid flow names"):
            parse_selected_flow_names(" , ")

    def test_get_load_enabled_flows_can_filter_by_name(self) -> None:
        filtered = get_load_enabled_flows([FLOW_LOGIN, FLOW_ANALYZE_LIST])
        self.assertEqual([flow.name for flow in filtered], [FLOW_LOGIN, FLOW_ANALYZE_LIST])

    def test_flow_definition_contains_expected_page_event_name(self) -> None:
        self.assertEqual(get_flow_definition(FLOW_DASHBOARD).page_event_name, "dashboard:ready")

    def test_load_measured_flow_decorator_records_flow_names(self) -> None:
        @load_measured_flow(FLOW_LOGIN, FLOW_ASSESS_LIST)
        def wrapper():
            return None

        self.assertEqual(
            getattr(wrapper, LOAD_MEASURED_FLOW_ATTR),
            (FLOW_LOGIN, FLOW_ASSESS_LIST),
        )


if __name__ == "__main__":
    unittest.main()
