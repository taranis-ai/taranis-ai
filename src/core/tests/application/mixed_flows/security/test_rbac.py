import uuid
from unittest.mock import Mock

import pytest

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
    def test_tag_filter_candidates_require_visible_non_report_tags_before_limit(
        self, client, session, auth_header_user_permissions, monkeypatch
    ):
        from core.model.filter_data import FilterData
        from core.model.news_item_attribute import NewsItemAttribute
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        visible_source, _, visible_item = create_rbac_source_story("filter-visible")
        _, _, acl_hidden_item = create_rbac_source_story("filter-acl-hidden")
        tlp_source, tlp_story, tlp_hidden_item = create_rbac_source_story("filter-tlp-hidden")
        role = Role.filter_by_name("User")
        role.tlp_level = TLPLevel.CLEAR
        grant_acl(role, ItemType.OSINT_SOURCE, visible_source.id)
        grant_acl(role, ItemType.OSINT_SOURCE, tlp_source.id)
        tlp_story.upsert_attribute(NewsItemAttribute("tlp_override", "red"))
        tlp_story.refresh_tlp()
        visible_item.set_tags([{"name": "10-public"}, {"name": "11-shared"}, {"name": "02-report-collision", "tag_type": "report_auto"}])
        acl_hidden_item.set_tags([{"name": "00-acl-hidden"}, {"name": "02-report-collision"}, {"name": "11-shared"}])
        tlp_hidden_item.set_tags([{"name": "01-tlp-hidden"}, {"name": "11-shared", "tag_type": "actor"}])
        db.session.commit()
        monkeypatch.setattr(FilterData, "LIST_LIMIT", 2)

        response = client.get("/api/assess/filter-lists", headers=auth_header_user_permissions)
        assert response.status_code == 200
        assert response.json["tags"] == ["10-public", "11-shared"]

    def test_selected_export_requires_read_access_to_every_item(self, client, session, auth_header_user_permissions):
        from core.model.news_item_attribute import NewsItemAttribute
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.story import Story

        source, story, _ = create_rbac_source_story("export-allowed")
        other_source, other_story, other_item = create_rbac_source_story("export-other")
        role = Role.filter_by_name("User")
        role.tlp_level = TLPLevel.CLEAR
        grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
        endpoint = "/api/assess/stories/export"

        for ids in ([story.id, "missing"], [story.id, other_story.id]):
            response = client.get(endpoint, headers=auth_header_user_permissions, query_string={"story_ids": ids})
            assert response.status_code == 404
            assert response.json == {"error": "One or more selected stories are unavailable"}
            assert "Content-Disposition" not in response.headers

        other_acl = grant_acl(role, ItemType.OSINT_SOURCE, other_source.id, read_only=True)
        response = client.get(
            endpoint, headers=auth_header_user_permissions, query_string={"story_ids": [other_story.id, story.id, other_story.id]}
        )
        assert response.status_code == 200
        assert response.json["total_count"] == 2
        assert [exported["id"] for exported in response.json["items"]] == [other_story.id, story.id]

        Story.group_stories([story.id, other_story.id])
        other_acl.item_id = "unrelated-source"
        db.session.commit()
        response = client.get(endpoint, headers=auth_header_user_permissions, query_string={"story_ids": story.id})
        assert response.status_code == 404
        assert response.json == {"error": "One or more selected stories are unavailable"}
        other_acl.item_id = other_source.id
        for target in (story, other_item):
            target.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
            db.session.commit()
            response = client.get(endpoint, headers=auth_header_user_permissions, query_string={"story_ids": story.id})
            assert response.status_code == 404
            assert response.json == {"error": "One or more selected stories are unavailable"}
            target.upsert_attribute(NewsItemAttribute(key="TLP", value="clear"))
            db.session.commit()

        assert client.get(endpoint, headers=auth_header_user_permissions, query_string={"story_ids": story.id}).status_code == 200

    @pytest.mark.parametrize("resource", ["report", "product"])
    def test_delete_requires_object_write_access(self, client, session, auth_header_user_permissions, resource):
        from core.model.permission import Permission
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        role = Role.filter_by_name("User")
        assert role is not None
        role.tlp_level = TLPLevel.RED
        for permission in Permission.get_bulk(["ANALYZE_DELETE", "PUBLISH_DELETE"]):
            if permission not in role.permissions:
                role.permissions.append(permission)
        if resource == "report":
            item = create_rbac_report_item("delete-access", TLPLevel.AMBER)
            item_type = ItemType.REPORT_ITEM_TYPE
            type_id = item.report_item_type_id
            url = f"/api/analyze/report-items/{item.id}"
        else:
            product_type = ProductType.filter_by_title("Default TEXT Presenter")
            assert product_type is not None
            item = Product(title="Delete access", product_type_id=product_type.id)
            db.session.add(item)
            db.session.commit()
            item_type = ItemType.PRODUCT_TYPE
            type_id = product_type.id
            url = f"/api/publish/products/{item.id}"

        acl = grant_acl(role, item_type, "unrelated-type")
        item_id = item.id
        for allowed_type in ["unrelated-type", type_id]:
            acl.item_id = allowed_type
            db.session.commit()
            response = client.delete(url, headers=auth_header_user_permissions)
            assert response.status_code == 403
            assert response.json == {"error": f"User is not allowed to delete {resource}"}
            assert type(item).get(item_id) is not None

        acl.read_only = False
        db.session.commit()
        if resource == "report":
            role.tlp_level = TLPLevel.CLEAR
            db.session.commit()
            assert client.delete(url, headers=auth_header_user_permissions).status_code == 403
            assert type(item).get(item_id) is not None
            role.tlp_level = TLPLevel.RED
            db.session.commit()

        assert client.delete(url, headers=auth_header_user_permissions).status_code == 200
        assert type(item).get(item_id) is None
        assert client.delete(url, headers=auth_header_user_permissions).status_code == 404

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
        editor_error, editor_status = ReportItem.get_editor_for_api(report_item_amber.id, clear_user)
        assert editor_status == 403
        assert editor_error == read_error

        blocked_report, update_error, update_status = ReportItem.get_report_item_and_check_permission(report_item_amber.id, clear_user)
        assert blocked_report is None
        assert update_status == 403
        assert update_error == {"error": "User is not allowed to update report"}

        read_data, read_status = ReportItem.get_for_api(report_item_amber.id, amber_user)
        assert read_status == 200
        assert read_data["id"] == report_item_amber.id
        editor_data, editor_status = ReportItem.get_editor_for_api(report_item_amber.id, amber_user)
        assert editor_status == 200
        assert editor_data["id"] == report_item_amber.id

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

        from core.model.news_item_attribute import NewsItemAttribute
        from core.service.story_operations import StoryOperationsService

        source, target = results[:2]
        source.upsert_attribute(NewsItemAttribute("tlp_override", "clear"))
        source.find_attribute_by_key("tlp_override").value = "invalid"
        item = source.news_items[0]
        item.upsert_attribute(NewsItemAttribute("TLP", "clear"))
        item.find_attribute_by_key("TLP").value = "invalid"
        db.session.commit()
        db.session.expire_all()
        assert item.tlp_level == TLPLevel.RED
        source.refresh_tlp()
        assert source.tlp_level == TLPLevel.RED
        StoryOperationsService.transfer_news_item_to_story(target, item, {})
        target.refresh_tlp()
        assert target.tlp_level == TLPLevel.RED
        db.session.commit()
        target.find_attribute_by_key("tlp_override").value = "invalid"
        split_id = Story.create_from_item(item)
        assert Story.get(split_id).tlp_level == TLPLevel.RED

        db.session.remove()


class TestRBACAclBehavior:
    @pytest.mark.parametrize("restriction", ["acl", "tlp"])
    def test_product_with_restricted_reports_allows_only_metadata_edits(
        self, client, session, auth_header_user_permissions, restriction, monkeypatch
    ):
        from core.managers import queue_manager
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.publisher_preset import PublisherPreset
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        report = create_rbac_report_item(f"product-choice-{restriction}", TLPLevel.RED if restriction == "tlp" else TLPLevel.CLEAR)
        role = Role.filter_by_name("User")
        role.tlp_level = TLPLevel.CLEAR
        grant_acl(role if restriction == "tlp" else Role.filter_by_name("Admin"), ItemType.REPORT_ITEM_TYPE, report.report_item_type_id)

        visible_type = ReportItemType(f"Visible report type {restriction}")
        session.add(visible_type)
        session.flush()
        grant_acl(role, ItemType.REPORT_ITEM_TYPE, visible_type.id)
        visible_report = ReportItem("Visible report", visible_type.id)
        session.add(visible_report)
        session.flush()
        product_type = ProductType.filter_by_title("Default TEXT Presenter")
        product_type.report_types = [visible_type, ReportItemType.get(report.report_item_type_id)]
        publisher = PublisherPreset.get_first(db.select(PublisherPreset))
        product = Product(
            "Restricted product",
            product_type.id,
            description="Original description",
            report_items=[report.id, visible_report.id],
            auto_publish=True,
            default_publisher=publisher.id,
        )
        product.render_result = "ZXhpc3RpbmcgcmVuZGVy"
        product.last_published_url = f"/reports/{product.id}"
        session.add(product)
        session.commit()
        original_report_ids = {report.id, visible_report.id}
        enqueue = Mock()
        monkeypatch.setattr(queue_manager.queue_manager, "enqueue_task", enqueue)
        monkeypatch.setattr(queue_manager.queue_manager, "enqueue_at", enqueue)

        response = client.get(
            "/api/publish/product-type-choices", headers=auth_header_user_permissions, query_string={"report_ids": [report.id]}
        )
        assert response.status_code == 404
        assert response.json == {"error": "Selected reports not found or not accessible"}

        for path in [f"products/{product.id}", f"product-metadata/{product.id}"]:
            detail = client.get(f"/api/publish/{path}", headers=auth_header_user_permissions)
            assert detail.status_code == 200
            assert detail.json["report_access_warning"] == Product.RESTRICTED_REPORTS_MESSAGE
            assert set(detail.json["report_items"]) == original_report_ids
            assert report.title not in str(detail.json["supported_reports"])
            assert visible_report.id in {item["id"] for item in detail.json["supported_reports"]}

        payload = {
            "title": "Updated metadata",
            "description": "Updated description",
            "product_type_id": product_type.id,
            "report_items": list(original_report_ids),
            "auto_publish": True,
            "default_publisher": publisher.id,
        }
        updated = client.put(f"/api/publish/products/{product.id}", headers=auth_header_user_permissions, json=payload)
        assert updated.status_code == 200
        assert updated.json["product"]["title"] == "Updated metadata"
        assert updated.json["product"]["description"] == "Updated description"
        assert updated.json["product"]["report_access_warning"] == Product.RESTRICTED_REPORTS_MESSAGE
        assert report.title not in str(updated.json["product"]["supported_reports"])
        for change in [{"report_items": []}, {"product_type_id": "another-type"}, {"auto_publish": False}, {"default_publisher": None}]:
            rejected = client.put(f"/api/publish/products/{product.id}", headers=auth_header_user_permissions, json={**payload, **change})
            assert rejected.status_code == 403
            assert rejected.json == {"error": Product.RESTRICTED_REPORTS_MESSAGE}

        for path in [f"products/{product.id}/render", f"products/{product.id}/publishers/{publisher.id}"]:
            rejected = client.post(f"/api/publish/{path}", headers=auth_header_user_permissions)
            assert rejected.status_code == 403
            assert rejected.json == {"error": Product.RESTRICTED_REPORTS_MESSAGE}
        copied = client.post("/api/publish/products", headers=auth_header_user_permissions, json={**payload, "title": "Forbidden copy"})
        assert copied.status_code == 404
        assert Product.get_first(db.select(Product).where(Product.title == "Forbidden copy")) is None
        empty_product = Product("Empty product", product_type.id)
        session.add(empty_product)
        session.commit()
        attached = client.put(f"/api/publish/products/{empty_product.id}", headers=auth_header_user_permissions, json=payload)
        assert attached.status_code == 404
        assert empty_product.report_items == []
        session.expire_all()
        assert {item.id for item in product.report_items} == original_report_ids
        assert product.render_result == "ZXhpc3RpbmcgcmVuZGVy"
        assert product.last_published_url == f"/reports/{product.id}"
        assert product.auto_publish is True
        assert product.default_publisher == publisher.id
        enqueue.assert_not_called()

        if restriction == "tlp":
            role.tlp_level = TLPLevel.RED
        else:
            grant_acl(role, ItemType.REPORT_ITEM_TYPE, report.report_item_type_id)
        session.commit()
        accessible = client.get(f"/api/publish/products/{product.id}", headers=auth_header_user_permissions)
        assert accessible.status_code == 200
        assert accessible.json["report_access_warning"] is None
        assert original_report_ids <= {item["id"] for item in accessible.json["supported_reports"]}
        assert client.put(f"/api/publish/products/{product.id}", headers=auth_header_user_permissions, json=payload).status_code == 200
        enqueue.assert_called_once()

    def test_product_choices_include_all_visible_products_without_render_data(self, client, session, auth_header_user_permissions):
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        visible_type = ProductType.filter_by_title("Default TEXT Presenter")
        hidden_type = ProductType.filter_by_title("CERT Daily Report")
        grant_acl(Role.filter_by_name("User"), ItemType.PRODUCT_TYPE, visible_type.id)
        grant_acl(Role.filter_by_name("Admin"), ItemType.PRODUCT_TYPE, hidden_type.id)
        products = [Product(f"Choice {index:02}", visible_type.id) for index in range(21)]
        hidden = Product("Hidden choice", hidden_type.id)
        session.add_all([*products, hidden])
        session.flush()

        response = client.get("/api/publish/product-choices", headers=auth_header_user_permissions)
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert {product.id for product in products} <= {item["id"] for item in items}
        assert hidden.id not in {item["id"] for item in items}
        assert all(set(item) == {"id", "title", "product_type_title"} for item in items)
        assert [item["title"] for item in items] == sorted(item["title"] for item in items)

        listed = client.get("/api/publish/products?search=Choice&fetch_all=true", headers=auth_header_user_permissions)
        assert listed.status_code == 200
        assert listed.json["total_count"] == 21
        assert {item["id"] for item in listed.json["items"]} == {item.id for item in products}
        types = client.get("/api/publish/product-type-choices", headers=auth_header_user_permissions)
        assert types.status_code == 200
        assert visible_type.id in {item["id"] for item in types.json["items"]}
        assert hidden_type.id not in {item["id"] for item in types.json["items"]}
        for path in [f"products/{hidden.id}", f"product-metadata/{hidden.id}", f"products/{hidden.id}/render"]:
            assert client.get(f"/api/publish/{path}", headers=auth_header_user_permissions).status_code == 403
        assert client.get(f"/api/publish/product-metadata/{products[0].id}", headers=auth_header_user_permissions).status_code == 200

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

    @pytest.mark.parametrize("operation", ["put", "patch", "reorder"])
    def test_story_updates_require_write_access_and_tlp(self, client, session, auth_header_user_permissions, operation):
        from core.model.role import Role
        from core.model.role_based_access import ItemType
        from core.model.story import Story
        from tests.application.support.builders import build_news_item_payload, create_story

        source, story, _ = create_rbac_source_story("order-write")
        other_source, other, _ = create_rbac_source_story("order-other")
        Story.group_stories([story.id, other.id])
        user_role = Role.filter_by_name("User")
        grant_acl(user_role, ItemType.OSINT_SOURCE, source.id, read_only=False)
        other_acl = grant_acl(user_role, ItemType.OSINT_SOURCE, other_source.id, read_only=True)
        suffix = "/news-item-order" if operation == "reorder" else ""
        endpoint = f"/api/assess/stories/{story.id}{suffix}"
        send = client.patch if operation == "patch" else client.put
        ids = [item.id for item in story.ordered_news_items]
        payload = {"news_item_ids": list(reversed(ids)), "expected_news_item_ids": ids}

        if operation != "reorder":
            payload = {"title": "Updated story"}
        original_title = story.title
        detail_url = f"/api/assess/stories/{story.id}"
        assert client.get(detail_url, headers=auth_header_user_permissions).json["can_edit"] is False
        assert send(endpoint, headers=auth_header_user_permissions, json=payload).status_code == 403
        db.session.refresh(story)
        assert story.title == original_title
        assert [item.id for item in story.ordered_news_items] == ids
        other_acl.read_only = False
        db.session.commit()
        permissions = list(user_role.permissions)
        user_role.permissions = [permission for permission in permissions if permission.code != "ASSESS_UPDATE"]
        db.session.commit()
        assert client.get(detail_url, headers=auth_header_user_permissions).json["can_edit"] is False
        user_role.permissions = permissions
        db.session.commit()
        assert client.get(detail_url, headers=auth_header_user_permissions).json["can_edit"] is True
        assert send(endpoint, headers=auth_header_user_permissions, json=payload).status_code == 200

        from core.model.news_item_attribute import NewsItemAttribute

        story.upsert_attribute(NewsItemAttribute(key="rt_id", value="123"))
        db.session.commit()
        assert client.get(detail_url, headers=auth_header_user_permissions).json["can_edit"] is False
        assert send(endpoint, headers=auth_header_user_permissions, json=payload).status_code == 403
        item_url = f"/api/assess/news-items/{story.news_items[0].id}"
        assert client.put(item_url, headers=auth_header_user_permissions, json={"title": "Blocked"}).status_code == 403
        assert client.put(f"{item_url}/tags", headers=auth_header_user_permissions, json=[]).status_code == 403

        restricted = create_story(news_items=[build_news_item_payload(source.id)], attributes=[{"key": "TLP", "value": "red"}])
        from core.model.news_item_attribute import NewsItemAttribute

        restricted.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
        db.session.commit()
        restricted_ids = [item.id for item in restricted.news_items]
        restricted_payload = (
            {"news_item_ids": restricted_ids, "expected_news_item_ids": restricted_ids} if operation == "reorder" else {"title": "Blocked"}
        )
        response = send(
            f"/api/assess/stories/{restricted.id}{suffix}",
            headers=auth_header_user_permissions,
            json=restricted_payload,
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("rt_managed", [False, True])
    def test_story_bot_action_rejects_read_only_source_access(self, client, session, auth_header_user_permissions, monkeypatch, rt_managed):
        from core.model.permission import Permission
        from core.model.role import Role
        from core.model.role_based_access import ItemType

        source, story, _ = create_rbac_source_story("bot-action-read-only")
        user_role = Role.filter_by_name("User")
        assert user_role is not None
        grant_acl(user_role, ItemType.OSINT_SOURCE, source.id, read_only=not rt_managed)
        if rt_managed:
            from core.model.news_item_attribute import NewsItemAttribute

            story.upsert_attribute(NewsItemAttribute(key="rt_id", value="123"))
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
