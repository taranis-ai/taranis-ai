from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

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
    pytest.param({"language": ("",)}, set(), id="language-empty"),
    pytest.param({"story_ids": ("grouped_flagged", "manual_important")}, {"grouped_flagged", "manual_important"}, id="story-ids"),
    pytest.param({"search": "Story Filter Extra Source Story"}, {"source_only"}, id="search-extra-title"),
    pytest.param({"search": "Anonymous News Item"}, {"manual_important"}, id="search-anonymous-title"),
    pytest.param({"changed_by": "me"}, {"grouped_flagged"}, id="changed-by-me"),
]


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

    @pytest.mark.parametrize(("filters", "expected_story_keys"), FILTER_CASES)
    def test_story_filters(self, client, auth_header, story_filter_data, filters, expected_story_keys):
        self._assert_filtered_story_ids(client, auth_header, story_filter_data, filters, expected_story_keys)

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
        from core.model.news_item_tag import NewsItemTag

        with app.app_context():
            tag = NewsItemTag.find_by_name(story_filter_data["tags"]["alpha"])
            assert tag is not None
            tag.tag_type = None
            db.session.commit()

        response = client.get(self.concat_url("filter-lists"), headers=auth_header)
        payload = self.assert_json_ok(response).get_json()

        assert story_filter_data["tags"]["alpha"] in payload["tags"]

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

    def test_filter_lists_languages_respect_source_acl(self, app, client, auth_header_user_permissions, fake_source, story_filter_data):
        from core.managers.db_manager import db
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSource
        from core.model.role import Role
        from core.model.role_based_access import ItemType, RoleBasedAccess
        from core.model.story import Story

        acl_ids = []
        restricted_source_id = str(uuid4())
        restricted_news_item_id = str(uuid4())
        restricted_story_id = None

        with app.app_context():
            restricted_source = OSINTSource(
                id=restricted_source_id,
                name="Restricted Language Source",
                description="Source restricted to admin role",
                type="rss_collector",
                parameters={"FEED_URL": "https://example.invalid/restricted-language.xml"},
            )
            db.session.add(restricted_source)
            db.session.commit()

            result, status = Story.add(
                {
                    "title": "Restricted Language Story",
                    "news_items": [
                        {
                            "id": restricted_news_item_id,
                            "title": "Restricted Language Story",
                            "content": "Restricted language content",
                            "source": "unit-test",
                            "link": "https://example.invalid/restricted-language",
                            "osint_source_id": restricted_source_id,
                            "language": "it",
                            "hash": NewsItem.get_hash(
                                title="Restricted Language Story",
                                link="https://example.invalid/restricted-language",
                            ),
                        }
                    ],
                }
            )
            assert status == 200
            restricted_story_id = result["story_id"]

            user_role = Role.filter_by_name("User")
            admin_role = Role.filter_by_name("Admin")
            assert user_role is not None
            assert admin_role is not None

            acl_specs = (
                ("visible-test-source", fake_source, user_role.id),
                ("visible-extra-source", story_filter_data["sources"]["source_only"], user_role.id),
                ("visible-manual-source", "manual", user_role.id),
                ("restricted-language-source", restricted_source_id, admin_role.id),
            )
            for name, item_id, role_id in acl_specs:
                acl = RoleBasedAccess(
                    name=f"{name}-{uuid4()}",
                    description="Filter-list language ACL test",
                    item_type=ItemType.OSINT_SOURCE,
                    item_id=item_id,
                    roles=[role_id],
                    read_only=True,
                    enabled=True,
                )
                db.session.add(acl)
                db.session.flush()
                acl_ids.append(acl.id)
            db.session.commit()

        try:
            response = client.get(self.concat_url("filter-lists"), headers=auth_header_user_permissions)
            payload = self.assert_json_ok(response).get_json()

            assert "it" not in payload["languages"]
            assert set(payload["languages"]) >= {"de", "en", "fr"}
        finally:
            with app.app_context():
                for acl_id in acl_ids:
                    RoleBasedAccess.delete(acl_id)
                if news_item := NewsItem.get(restricted_news_item_id):
                    db.session.delete(news_item)
                if restricted_story_id and (story := Story.get(restricted_story_id)):
                    db.session.delete(story)
                if source := OSINTSource.get(restricted_source_id):
                    db.session.delete(source)
                db.session.commit()
