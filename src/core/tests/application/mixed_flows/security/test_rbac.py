import uuid
from unittest.mock import Mock

from core.managers.db_manager import db
from core.model.role import TLPLevel
from tests.application.support.rbac import (
    admin_ops_user,
    create_rbac_report_item,
    create_rbac_source_group,
    create_rbac_source_story,
    grant_acl,
    visible_story_ids,
)


class TestRBAC:
    def test_news_item_without_source_uses_default_tlp_setting(self, app):
        from core.model.news_item import NewsItem
        from core.model.settings import Settings

        with app.app_context():
            settings = Settings.get_settings_entry()
            assert settings is not None
            original_settings = dict(settings.settings or {})

            try:
                settings.settings = Settings.with_defaults(original_settings | {"default_tlp_level": TLPLevel.RED.value})
                db.session.commit()

                news_item = NewsItem(title="No source", content="content", osint_source_id="missing-source", hash="no-source-hash")
                news_item.osint_source = None

                assert news_item.tlp_level == TLPLevel.RED
            finally:
                settings.settings = original_settings
                db.session.commit()

    def test_report_item_tlp_gate_blocks_read_and_update_below_required_level(self, report_items):
        from core.model.report_item import ReportItem

        _, report_item_amber, _, _ = report_items

        clear_user = Mock()
        clear_user.id = "clear-user"
        clear_user.get_highest_tlp.return_value = TLPLevel.CLEAR

        amber_user = Mock()
        amber_user.id = "amber-user"
        amber_user.get_highest_tlp.return_value = TLPLevel.AMBER

        read_error, read_status = ReportItem.get_for_api(report_item_amber.id, clear_user)
        assert read_status == 403
        assert read_error == {"error": "User is not allowed to read report"}

        blocked_report, update_error, update_status = ReportItem.get_report_item_and_check_permission(report_item_amber.id, clear_user)
        assert blocked_report is None
        assert update_status == 403
        assert update_error == {"error": "User is not allowed to update report"}

        read_data, read_status = ReportItem.get_for_api(report_item_amber.id, amber_user)
        assert read_status == 200
        assert read_data["id"] == report_item_amber.id

        allowed_report, update_error, update_status = ReportItem.get_report_item_and_check_permission(report_item_amber.id, amber_user)
        assert allowed_report is not None
        assert allowed_report.id == report_item_amber.id
        assert update_status == 200
        assert update_error == {}

    def test_filter_report_query_with_tlp(self, report_items):
        from core.model.report_item import ReportItem
        from core.service.role_based_access import RoleBasedAccessService

        report_item_clear, report_item_amber, report_item_red, report_item_without_TLP = report_items

        mock_user = Mock()
        query = db.select(ReportItem)

        # User has TLP:Clear -> Should see only Report Item with TLP:Clear
        mock_user.get_highest_tlp.return_value = TLPLevel.CLEAR
        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results
        result_ids = {r.id for r in results}
        assert {report_item_clear.id, report_item_without_TLP.id} == result_ids

        # User has TLP:Green -> Should see only Report Item with TLP:Clear
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results

        result_ids = {r.id for r in results}
        assert {report_item_clear.id, report_item_without_TLP.id} == result_ids

        # User has TLP:Amber -> Should see Report Items with TLP:Clear & TLP:Amber
        mock_user.get_highest_tlp.return_value = TLPLevel.AMBER
        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results
        result_ids = {r.id for r in results}
        assert {report_item_clear.id, report_item_amber.id, report_item_without_TLP.id} == result_ids

        # User has TLP:Red -> Should see all Report Items
        mock_user.get_highest_tlp.return_value = TLPLevel.RED

        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results
        result_ids = {r.id for r in results}
        assert {report_item_clear.id, report_item_amber.id, report_item_red.id, report_item_without_TLP.id} == result_ids

    def test_filter_query_with_tlp(self, stories_with_tlp):
        from core.model.story import Story
        from core.service.role_based_access import RoleBasedAccessService

        mock_user = Mock()
        query = db.select(Story).where(Story.id.in_(stories_with_tlp["story_ids"]))

        # User has only TLP level Clear -> should see only the TLP Clear story
        mock_user.get_highest_tlp.return_value = TLPLevel.CLEAR
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_titles = {n.title for story in results for n in story.news_items}
        assert result_titles == {"Plain News Item"}

        # User has TLP level Green -> should see the TLP Green and Clear story
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_titles = {n.title for story in results for n in story.news_items}
        assert result_titles == {"TLP News Item", "Plain News Item"}

        # User has TLP level Red -> should see all stories
        mock_user.get_highest_tlp.return_value = TLPLevel.RED
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_titles = {n.title for story in results for n in story.news_items}
        assert result_titles == {"TLP News Item", "Plain News Item", "Another TLP News Item"}

        db.session.remove()


class TestRBACAclBehavior:
    def test_admin_operations_bypasses_acl_filtering_but_not_tlp(self, session):
        from core.model.report_item import ReportItem
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        _, story_a, _ = create_rbac_source_story("admin-allowed")
        source_b, story_b, _ = create_rbac_source_story("admin-denied-without-bypass")
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE, source_b.id)

        admin = User.find_by_name("admin")
        assert admin is not None
        assert visible_story_ids([story_a.id, story_b.id], admin) == {story_a.id, story_b.id}

        report_item_clear = create_rbac_report_item("Clear")
        report_item_amber = create_rbac_report_item("Amber", TLPLevel.AMBER)
        admin_ops_clear_user = admin_ops_user(TLPLevel.CLEAR)
        grant_acl(user_role, ItemType.REPORT_ITEM_TYPE, "unrelated-report-type")

        read_data, read_status = ReportItem.get_for_api(report_item_clear.id, admin_ops_clear_user)
        assert read_status == 200
        assert read_data["id"] == report_item_clear.id

        read_error, read_status = ReportItem.get_for_api(report_item_amber.id, admin_ops_clear_user)
        assert read_status == 403
        assert read_error == {"error": "User is not allowed to read report"}

    def test_config_endpoints_ignore_content_acls(self, client, session, auth_header_user_permissions):
        from core.model.permission import Permission
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        source, _, _ = create_rbac_source_story("config-visible")
        group = create_rbac_source_group("RBAC Config Visible Group", [source])
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE, str(uuid.uuid4()))
        grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, "unrelated-group")
        user_role.permissions = [
            *user_role.permissions,
            *Permission.get_bulk(["CONFIG_OSINT_SOURCE_ACCESS", "CONFIG_OSINT_SOURCE_GROUP_UPDATE"]),
        ]
        db.session.flush()

        response = client.get(f"/api/config/osint-sources?search={source.name}", headers=auth_header_user_permissions)
        assert response.status_code == 200
        assert {item["id"] for item in response.json["items"]} == {source.id}

        response = client.put(
            f"/api/config/osint-source-groups/{group.id}",
            json={"name": "RBAC Config Updated Group", "osint_sources": [source.id], "word_lists": []},
            headers=auth_header_user_permissions,
        )
        assert response.status_code == 201
        assert response.json["id"] == group.id

    def test_direct_source_acl_filters_assess_stories_and_news_items(self, session):
        from core.model.news_item import NewsItem
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        source_a, story_a, item_a = create_rbac_source_story("direct-allowed")
        _, story_b, item_b = create_rbac_source_story("direct-denied")
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE, source_a.id)

        assert visible_story_ids([story_a.id, story_b.id], user) == {story_a.id}

        payload, status = NewsItem.get_all_for_api({"search": "RBAC direct", "limit": 20, "offset": 0}, user=user)
        assert status == 200
        assert {item["id"] for item in payload["items"]} == {item_a.id}

        detail_error, detail_status = NewsItem.get_for_api(item_b.id, user)
        assert detail_status == 403
        assert detail_error == {"error": "User does not have access to this news item"}

    def test_source_group_acl_inherits_to_assess_content_and_filter_lists(self, session):
        from core.model.osint_source import OSINTSource, OSINTSourceGroup
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        source_a, story_a, _ = create_rbac_source_story("group-allowed")
        _, story_b, _ = create_rbac_source_story("group-denied")
        group = create_rbac_source_group("RBAC Group Allowed", [source_a])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, group.id)

        assert visible_story_ids([story_a.id, story_b.id], user) == {story_a.id}

        source_payload, source_status = OSINTSource.get_all_for_assess_api(user=user)
        assert source_status == 200
        assert {item["id"] for item in source_payload["items"]} == {source_a.id}

        group_payload, group_status = OSINTSourceGroup.get_all_for_assess_api(user=user)
        assert group_status == 200
        assert {item["id"] for item in group_payload["items"]} == {group.id}

    def test_source_group_wildcard_acl_inherits_to_all_sources(self, session):
        from core.model.osint_source import OSINTSource
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        source_a, story_a, _ = create_rbac_source_story("wildcard-grouped")
        source_b, story_b, _ = create_rbac_source_story("wildcard-ungrouped")
        create_rbac_source_group("RBAC Wildcard Group", [source_a])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, "*")

        assert visible_story_ids([story_a.id, story_b.id], user) == {story_a.id, story_b.id}

        source_payload, source_status = OSINTSource.get_all_for_assess_api(user=user)
        assert source_status == 200
        assert {source_a.id, source_b.id}.issubset({item["id"] for item in source_payload["items"]})

    def test_inherited_group_acl_preserves_read_only_for_write_checks(self, session):
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        source, _, item = create_rbac_source_story("group-write")
        group = create_rbac_source_group("RBAC Group Write", [source])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        acl = grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, group.id, read_only=True)

        assert item.allowed_with_acl(user, require_write_access=False)
        assert not item.allowed_with_acl(user, require_write_access=True)

        acl.read_only = False
        db.session.commit()
        assert item.allowed_with_acl(user, require_write_access=True)

    def test_story_bot_action_rejects_read_only_source_access(self, client, session, auth_header_user_permissions, monkeypatch):
        from core.model.permission import Permission
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        source, story, _ = create_rbac_source_story("bot-action-read-only")
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE, source.id, read_only=True)
        for permission in Permission.get_bulk(["ASSESS_UPDATE"]):
            if permission not in user_role.permissions:
                user_role.permissions.append(permission)
        db.session.flush()
        blocked_enqueue = Mock(side_effect=AssertionError("should not enqueue"))
        monkeypatch.setattr("core.api.assess.queue_manager.queue_manager.execute_bot_task", blocked_enqueue)

        response = client.post(
            "/api/assess/stories/botactions",
            headers=auth_header_user_permissions,
            json={"bot_id": "summary_bot", "story_ids": [story.id]},
        )

        assert response.status_code == 403
        assert response.json == {"error": "User does not have write access to all requested stories"}
        blocked_enqueue.assert_not_called()

    def test_report_bot_action_rejects_read_only_report_access(self, client, session, auth_header_user_permissions, monkeypatch):
        from core.model.permission import Permission
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        report = create_rbac_report_item("bot-action-read-only")
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        grant_acl(user_role, ItemType.REPORT_ITEM_TYPE, report.report_item_type_id, read_only=True)
        for permission in Permission.get_bulk(["ANALYZE_UPDATE"]):
            if permission not in user_role.permissions:
                user_role.permissions.append(permission)
        db.session.flush()
        blocked_enqueue = Mock(side_effect=AssertionError("should not enqueue"))
        monkeypatch.setattr("core.api.analyze.queue_manager.queue_manager.execute_bot_task", blocked_enqueue)

        response = client.post(
            "/api/analyze/report-items/botactions",
            headers=auth_header_user_permissions,
            json={"bot_id": "summary_bot", "report_ids": [report.id]},
        )

        assert response.status_code == 403
        assert response.json == {"error": "User does not have write access to all requested reports"}
        blocked_enqueue.assert_not_called()
