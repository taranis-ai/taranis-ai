import uuid
from unittest.mock import Mock

from core.managers.db_manager import db
from core.model.role import TLPLevel


def _create_source_story(label: str):
    from core.model.news_item import NewsItem
    from core.model.osint_source import OSINTSource
    from core.model.story import Story

    source = OSINTSource(
        id=str(uuid.uuid4()),
        name=f"RBAC {label} Source",
        description="RBAC test source",
        type="rss_collector",
        parameters={"FEED_URL": f"https://example.invalid/{label}.xml"},
    )
    db.session.add(source)
    db.session.flush()

    story_payload = {
        "title": f"RBAC {label} Story",
        "news_items": [
            {
                "id": str(uuid.uuid4()),
                "title": f"RBAC {label} News",
                "content": f"RBAC {label} Content",
                "source": "unit-test",
                "link": f"https://example.invalid/{label}",
                "osint_source_id": source.id,
                "hash": NewsItem.get_hash(title=f"RBAC {label} News", link=f"https://example.invalid/{label}"),
                "collected": "2025-01-01T00:00:00",
                "published": "2025-01-01T00:00:00",
            }
        ],
    }
    result, status = Story.add(story_payload)
    assert status == 200
    story = Story.get(result["story_id"])
    assert story is not None
    assert story.news_items
    return source, story, story.news_items[0]


def _create_source_group(name: str, sources):
    from core.model.osint_source import OSINTSourceGroup

    group = OSINTSourceGroup(
        id=str(uuid.uuid4()),
        name=name,
        description="RBAC test source group",
    )
    group.osint_sources = list(sources)
    db.session.add(group)
    db.session.commit()
    return group


def _grant_acl(role, item_type, item_id: str, read_only: bool = True):
    from core.model.role_based_access import RoleBasedAccess

    acl = RoleBasedAccess(
        id=str(uuid.uuid4()),
        name=f"RBAC Test ACL {uuid.uuid4().hex}",
        description="RBAC test ACL",
        item_type=item_type,
        item_id=item_id,
        roles=[role.id],
        read_only=read_only,
        enabled=True,
    )
    db.session.add(acl)
    db.session.commit()
    return acl


def _create_report_item(label: str, tlp_level: TLPLevel | None = None):
    from core.model.report_item import ReportItem, ReportItemAttribute
    from core.model.report_item_type import ReportItemType

    report_type = ReportItemType.get_by_title("OSINT Report")
    assert report_type is not None

    report_item, status = ReportItem.add(
        {
            "id": str(uuid.uuid4()),
            "title": f"RBAC {label} Report",
            "completed": False,
            "report_item_type_id": report_type.id,
        },
        None,
    )
    assert status == 200
    assert isinstance(report_item, ReportItem)

    if tlp_level and (tlp_attribute := ReportItemAttribute.find_attribute_by_title(report_item.id, "TLP")):
        report_item.update_attributes({str(tlp_attribute.id): tlp_level.value}, True)

    return report_item


def _visible_story_ids(story_ids: list[str], user) -> set[str]:
    from core.model.story import Story

    payload, status = Story.get_by_filter_json({"story_ids": story_ids, "no_count": True}, user)
    assert status == 200
    return {item["id"] for item in payload["items"]}


class TestRBAC:
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

        _, story_a, _ = _create_source_story("admin-allowed")
        source_b, story_b, _ = _create_source_story("admin-denied-without-bypass")
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        _grant_acl(user_role, ItemType.OSINT_SOURCE, source_b.id)

        admin = User.find_by_name("admin")
        assert admin is not None
        assert _visible_story_ids([story_a.id, story_b.id], admin) == {story_a.id, story_b.id}

        report_item_clear = _create_report_item("Clear")
        report_item_amber = _create_report_item("Amber", TLPLevel.AMBER)
        admin_ops_clear_user = Mock()
        admin_ops_clear_user.get_permissions.return_value = ["ADMIN_OPERATIONS"]
        admin_ops_clear_user.get_highest_tlp.return_value = TLPLevel.CLEAR
        _grant_acl(user_role, ItemType.REPORT_ITEM_TYPE, "unrelated-report-type")

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

        source, _, _ = _create_source_story("config-visible")
        group = _create_source_group("RBAC Config Visible Group", [source])
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        _grant_acl(user_role, ItemType.OSINT_SOURCE, str(uuid.uuid4()))
        _grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, "unrelated-group")
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

        source_a, story_a, item_a = _create_source_story("direct-allowed")
        _, story_b, item_b = _create_source_story("direct-denied")
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        _grant_acl(user_role, ItemType.OSINT_SOURCE, source_a.id)

        assert _visible_story_ids([story_a.id, story_b.id], user) == {story_a.id}

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

        source_a, story_a, _ = _create_source_story("group-allowed")
        _, story_b, _ = _create_source_story("group-denied")
        group = _create_source_group("RBAC Group Allowed", [source_a])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        _grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, group.id)

        assert _visible_story_ids([story_a.id, story_b.id], user) == {story_a.id}

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

        source_a, story_a, _ = _create_source_story("wildcard-grouped")
        source_b, story_b, _ = _create_source_story("wildcard-ungrouped")
        _create_source_group("RBAC Wildcard Group", [source_a])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        _grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, "*")

        assert _visible_story_ids([story_a.id, story_b.id], user) == {story_a.id, story_b.id}

        source_payload, source_status = OSINTSource.get_all_for_assess_api(user=user)
        assert source_status == 200
        assert {source_a.id, source_b.id}.issubset({item["id"] for item in source_payload["items"]})

    def test_inherited_group_acl_preserves_read_only_for_write_checks(self, session):
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.user import User

        source, _, item = _create_source_story("group-write")
        group = _create_source_group("RBAC Group Write", [source])
        user = User.find_by_name("user")
        user_role = Role.filter_by_name("User")
        assert user is not None
        assert user_role is not None
        acl = _grant_acl(user_role, ItemType.OSINT_SOURCE_GROUP, group.id, read_only=True)

        assert item.allowed_with_acl(user, require_write_access=False)
        assert not item.allowed_with_acl(user, require_write_access=True)

        acl.read_only = False
        db.session.commit()
        assert item.allowed_with_acl(user, require_write_access=True)
