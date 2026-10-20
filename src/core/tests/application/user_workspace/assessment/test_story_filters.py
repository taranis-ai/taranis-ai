from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

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
    pytest.param({"relevant": "true"}, {"grouped_flagged", "manual_important"}, id="relevant-true"),
    pytest.param({"relevant": "false"}, {"grouped_plain", "source_only"}, id="relevant-false"),
    pytest.param({"in_report": "true"}, {"grouped_flagged"}, id="in-report-true"),
    pytest.param({"in_report": "false"}, {"grouped_plain", "manual_important", "source_only"}, id="in-report-false"),
    pytest.param({"tags": ("alpha",)}, {"grouped_flagged"}, id="tag-alpha"),
    pytest.param({"tags": ("beta",)}, {"grouped_plain"}, id="tag-beta"),
    pytest.param({"language": ("english",)}, {"grouped_flagged", "manual_important"}, id="language-english"),
    pytest.param({"language": ("german", "french")}, {"grouped_plain", "source_only"}, id="language-multiple"),
    pytest.param({"language": ("spanish",)}, set(), id="language-unknown"),
    pytest.param({"source": ("grouped",), "language": ("french",)}, set(), id="source-and-language"),
    pytest.param({"group": ("primary",), "language": ("german",)}, {"grouped_plain"}, id="group-and-language"),
    pytest.param({"language": ("",)}, set(), id="language-empty"),
    pytest.param({"story_ids": ("grouped_flagged", "manual_important")}, {"grouped_flagged", "manual_important"}, id="story-ids"),
    pytest.param({"search": "Story Filter Extra Source Story"}, {"source_only"}, id="search-extra-title"),
    pytest.param({"search": "Anonymous News Item"}, {"manual_important"}, id="search-anonymous-title"),
    pytest.param({"changed_by": "me"}, {"grouped_flagged"}, id="changed-by-me"),
]


def test_tag_suggestions_rank_exact_matches_then_distinct_story_counts(client, auth_header, session):
    from core.model.news_item_tag import NewsItemTag
    from tests.application.support.builders import build_news_item_payload, create_story

    stories = [create_story(news_items=[build_news_item_payload()]) for _ in range(2)]
    item = stories[0].news_items[0]
    item.tags.extend(
        [NewsItemTag("USA"), NewsItemTag("Cusa", ""), NewsItemTag("50%_& #"), NewsItemTag("50xx")]
        + [NewsItemTag("Ausa", tag_type) for tag_type in ("misc", "actor", "location")]
        + [NewsItemTag(f"zusa-{index:02}") for index in range(25)]
    )
    for story in stories:
        story.news_items[0].tags.append(NewsItemTag("Busa"))
    session.commit()

    response = client.get("/api/assess/taglist", headers=auth_header, query_string={"search": " usa "})
    assert response.status_code == 200
    tags = response.get_json()
    assert tags == ["USA", "Busa", "Ausa", "Cusa"] + [f"zusa-{index:02}" for index in range(16)]

    response = client.get("/api/assess/taglist", headers=auth_header, query_string={"search": "USA", "limit": 1})
    assert response.status_code == 200
    assert response.get_json() == ["USA"]
    response = client.get("/api/assess/taglist", headers=auth_header, query_string={"search": "usa", "limit": 2, "offset": 1})
    assert response.status_code == 200
    assert response.get_json() == ["Busa", "Ausa"]
    response = client.get("/api/assess/taglist", headers=auth_header, query_string={"search": "50%_"})
    assert response.status_code == 200
    assert response.get_json() == ["50%_& #"]
    response = client.get("/api/assess/taglist", headers=auth_header, query_string={"search": "missing-suggestion"})
    assert response.status_code == 200
    assert response.get_json() == []


class TestStoryFilters(BaseTest):
    base_uri = "/api/assess"
    _multi_value_filters = frozenset({"source", "group", "story_ids", "tags", "language"})

    @classmethod
    def _resolve_filter_values(cls, key: str, raw_values: Iterable[str], story_filter_data: dict) -> list[str]:
        lookup = {
            "source": story_filter_data["sources"],
            "group": story_filter_data["groups"],
            "story_ids": story_filter_data["stories"],
            "tags": story_filter_data["tags"],
            "language": story_filter_data["languages"],
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
        assert payload["counts"]["read_count"] == sum(bool(item["read"]) for item in payload["items"])
        assert payload["counts"]["important_count"] == sum(bool(item["important"]) for item in payload["items"])
        assert payload["counts"]["in_reports_count"] == sum(item["in_reports_count"] for item in payload["items"])

    @pytest.mark.parametrize(("filters", "expected_story_keys"), FILTER_CASES)
    def test_story_filters(self, client, auth_header, story_filter_data, filters, expected_story_keys):
        self._assert_filtered_story_ids(client, auth_header, story_filter_data, filters, expected_story_keys)

    @pytest.mark.parametrize("sort", ["date_desc", "date_asc", "relevance", "updated_desc", "updated_asc"])
    def test_paging_preserves_counts_and_breaks_sort_ties_by_id(self, app, client, auth_header, story_filter_data, sort):
        from core.managers.db_manager import db
        from core.model.story import Story

        story_ids = list(story_filter_data["stories"].values())
        with app.app_context():
            for story_id in story_ids:
                story = Story.get(story_id)
                story.title = "Same sort values"
                story.created = story.updated = datetime(2025, 1, 1)
                story.relevance = 0
            db.session.commit()

        expected = sorted(story_ids, reverse=not sort.endswith("_asc"))
        response = client.get(self.concat_url("stories"), headers=auth_header, query_string={"sort": sort, "limit": 2, "page": 1})
        payload = self.assert_json_ok(response).get_json()
        assert [item["id"] for item in payload["items"]] == expected[2:]
        assert payload["counts"]["total_count"] == 4
        assert payload["counts"]["read_count"] == 2
        assert payload["counts"]["important_count"] == 2
        assert payload["counts"]["in_reports_count"] == 1

    def test_filter_lists_include_news_item_languages(self, client, auth_header, story_filter_data):
        response = client.get(self.concat_url("filter-lists"), headers=auth_header)
        payload = self.assert_json_ok(response).get_json()

        assert payload["languages"] == sorted(story_filter_data["languages"].values())
        source_ids = {item["id"] for item in payload["sources"]}
        assert set(payload["languages"]) == {"de", "en", "fr"}
        assert "filter-alpha" in payload["tags"]
        assert story_filter_data["sources"]["source_only"] in source_ids

    def test_filter_lists_include_untyped_tags(self, app, client, auth_header, story_filter_data):
        from core.managers.db_manager import db
        from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster

        with app.app_context():
            tag = NewsItemTag.find_by_name(story_filter_data["tags"]["alpha"])
            assert tag is not None
            original_tag_type = tag.tag_type
            summary_keys = NewsItemTag.get_summary_keys_for_tag_types(tag.name, original_tag_type, None)
            tag.tag_type = None
            db.session.flush()
            NewsItemTagCluster.refresh_for_keys(summary_keys)
            db.session.commit()

        try:
            response = client.get(self.concat_url("filter-lists"), headers=auth_header)
            payload = self.assert_json_ok(response).get_json()

            assert story_filter_data["tags"]["alpha"] in payload["tags"]
        finally:
            with app.app_context():
                tag = NewsItemTag.find_by_name(story_filter_data["tags"]["alpha"])
                assert tag is not None
                tag.tag_type = original_tag_type
                db.session.flush()
                NewsItemTagCluster.refresh_for_keys(summary_keys)
                db.session.commit()

    def test_filter_lists_use_tag_summaries_for_names(self, app, client, auth_header, story_filter_data):
        from core.managers.db_manager import db
        from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster
        from core.model.story import Story

        with app.app_context():
            grouped_plain = Story.get(story_filter_data["stories"]["grouped_plain"])
            source_only = Story.get(story_filter_data["stories"]["source_only"])
            assert grouped_plain is not None
            assert source_only is not None
            original_grouped_tags = [tag.to_dict() for tag in grouped_plain.news_items[0].tags]
            original_source_tags = [tag.to_dict() for tag in source_only.news_items[0].tags]

            grouped_plain.news_items[0].set_tags([{"name": story_filter_data["tags"]["alpha"], "tag_type": "misc"}], replace=False)
            source_only.news_items[0].set_tags([{"name": "filter-report-only", "tag_type": "report_auto"}], replace=False)

            tag = NewsItemTag.find_by_name(story_filter_data["tags"]["alpha"])
            assert tag is not None
            original_tag_type = tag.tag_type
            summary_keys = NewsItemTag.get_summary_keys_for_tag_types(tag.name, original_tag_type, None)
            tag.tag_type = None
            db.session.flush()
            NewsItemTagCluster.refresh_for_keys(summary_keys)
            db.session.commit()

        try:
            response = client.get(self.concat_url("filter-lists"), headers=auth_header)
            payload = self.assert_json_ok(response).get_json()

            assert payload["tags"].count(story_filter_data["tags"]["alpha"]) == 1
            assert story_filter_data["tags"]["alpha"] in payload["tags"]
            assert "filter-report-only" not in payload["tags"]
        finally:
            with app.app_context():
                grouped_plain = Story.get(story_filter_data["stories"]["grouped_plain"])
                source_only = Story.get(story_filter_data["stories"]["source_only"])
                assert grouped_plain is not None
                assert source_only is not None

                grouped_plain.news_items[0].set_tags(original_grouped_tags, replace=True, update_story=False, commit=False)
                source_only.news_items[0].set_tags(original_source_tags, replace=True, update_story=False, commit=False)
                tag = NewsItemTag.find_by_name(story_filter_data["tags"]["alpha"])
                if tag is not None:
                    tag.tag_type = original_tag_type
                db.session.flush()
                NewsItemTagCluster.refresh_for_keys(summary_keys)
                db.session.commit()

    def test_filter_lists_reflect_language_changes_immediately(self, app, client, auth_header, story_filter_data):
        from core.managers.db_manager import db
        from core.model.story import Story

        source_only_id = story_filter_data["stories"]["source_only"]
        with app.app_context():
            source_only = Story.get(source_only_id)
            assert source_only is not None
            original_language = source_only.news_items[0].language
            source_only.news_items[0].language = "ES"
            db.session.commit()

        try:
            response = client.get(self.concat_url("filter-lists"), headers=auth_header)
            payload = self.assert_json_ok(response).get_json()

            assert set(payload["languages"]) == {"de", "en", "es"}
        finally:
            with app.app_context():
                source_only = Story.get(source_only_id)
                assert source_only is not None
                source_only.news_items[0].language = original_language
                db.session.commit()

    def test_language_filter_matches_legacy_case_variants(self, app, client, auth_header, story_filter_data):
        from core.managers.db_manager import db
        from core.model.story import Story

        source_only_id = story_filter_data["stories"]["source_only"]
        with app.app_context():
            source_only = Story.get(source_only_id)
            assert source_only is not None
            original_language = source_only.news_items[0].language
            source_only.news_items[0].language = "ES"
            db.session.commit()

        try:
            self._assert_filtered_story_ids(client, auth_header, story_filter_data, {"language": ("es",)}, {"source_only"})
        finally:
            with app.app_context():
                source_only = Story.get(source_only_id)
                assert source_only is not None
                source_only.news_items[0].language = original_language
                db.session.commit()
