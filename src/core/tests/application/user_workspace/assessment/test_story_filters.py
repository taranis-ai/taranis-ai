from __future__ import annotations

from collections.abc import Iterable

import pytest

from tests.application.support.api_test_base import BaseTest


FILTER_CASES = [
    pytest.param({"source": ("grouped",)}, {"grouped_flagged", "grouped_plain"}, id="source-grouped"),
    pytest.param({"group": ("primary",)}, {"grouped_flagged", "grouped_plain"}, id="group-primary"),
    pytest.param({"source": ("source_only",)}, {"source_only"}, id="source-only"),
    pytest.param(
        {"source": ("source_only",), "group": ("primary",)},
        {"grouped_flagged", "grouped_plain", "source_only"},
        id="source-or-group",
    ),
    pytest.param(
        {"source": ("source_only",), "group": ("primary",), "read": "true"},
        {"grouped_flagged", "source_only"},
        id="source-or-group-and-read",
    ),
    pytest.param(
        {"source": ("source_only",), "group": ("primary",), "important": "true"},
        {"grouped_flagged"},
        id="source-or-group-and-important",
    ),
    pytest.param({"read": "true"}, {"grouped_flagged", "source_only"}, id="read-true"),
    pytest.param({"read": "false"}, {"grouped_plain", "manual_important"}, id="read-false"),
    pytest.param({"important": "true"}, {"grouped_flagged", "manual_important"}, id="important-true"),
    pytest.param({"important": "false"}, {"grouped_plain", "source_only"}, id="important-false"),
    pytest.param({"relevant": "true"}, {"grouped_flagged", "source_only"}, id="relevant-true"),
    pytest.param({"relevant": "false"}, {"grouped_plain", "manual_important"}, id="relevant-false"),
    pytest.param({"in_report": "true"}, {"grouped_flagged"}, id="in-report-true"),
    pytest.param({"in_report": "false"}, {"grouped_plain", "manual_important", "source_only"}, id="in-report-false"),
    pytest.param({"tags": ("alpha",)}, {"grouped_flagged"}, id="tag-alpha"),
    pytest.param({"tags": ("beta",)}, {"grouped_plain"}, id="tag-beta"),
    pytest.param({"story_ids": ("grouped_flagged", "manual_important")}, {"grouped_flagged", "manual_important"}, id="story-ids"),
    pytest.param({"search": "Story Filter Extra Source Story"}, {"source_only"}, id="search-extra-title"),
    pytest.param({"search": "Anonymous News Item"}, {"manual_important"}, id="search-anonymous-title"),
]


class TestStoryFilters(BaseTest):
    base_uri = "/api/assess"
    _multi_value_filters = {"source", "group", "story_ids", "tags"}

    @classmethod
    def _resolve_filter_values(cls, key: str, raw_values: Iterable[str], story_filter_data: dict) -> list[str]:
        lookup = {
            "source": story_filter_data["sources"],
            "group": story_filter_data["groups"],
            "story_ids": story_filter_data["stories"],
            "tags": story_filter_data["tags"],
        }.get(key, {})
        return [lookup.get(value, value) for value in raw_values]

    @classmethod
    def _build_query_string(cls, filters: dict[str, str | tuple[str, ...]], story_filter_data: dict) -> list[tuple[str, str]]:
        query_string: list[tuple[str, str]] = []
        for key, raw_value in filters.items():
            values = raw_value if isinstance(raw_value, tuple) else (raw_value,)
            resolved_values = cls._resolve_filter_values(key, values, story_filter_data)
            if key in cls._multi_value_filters:
                query_string.extend((key, value) for value in resolved_values)
            else:
                query_string.append((key, resolved_values[0]))
        return query_string

    def _assert_filtered_story_ids(
        self,
        client,
        auth_header,
        story_filter_data: dict,
        filters: dict[str, str | tuple[str, ...]],
        expected_story_keys: set[str],
    ) -> None:
        response = client.get(
            self.concat_url("stories"),
            headers=auth_header,
            query_string=self._build_query_string(filters, story_filter_data),
        )
        payload = self.assert_json_ok(response).get_json()

        expected_ids = {story_filter_data["stories"][story_key] for story_key in expected_story_keys}
        actual_ids = {item["id"] for item in payload["items"]}

        assert payload["counts"]["total_count"] == len(expected_ids)
        assert actual_ids == expected_ids

    @pytest.mark.parametrize(("filters", "expected_story_keys"), FILTER_CASES)
    def test_story_filters(self, client, auth_header, story_filter_data, filters, expected_story_keys):
        self._assert_filtered_story_ids(client, auth_header, story_filter_data, filters, expected_story_keys)
