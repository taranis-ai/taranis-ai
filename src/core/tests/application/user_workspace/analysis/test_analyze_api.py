from copy import deepcopy
from uuid import uuid4

import pytest

from tests.application.support.api_test_base import BaseTest


def build_publish_product_payload(
    resources, story_ids, *, report_title=None, product_title=None, attribute_overrides=None, **product_overrides
):
    payload = {
        "report": {
            "title": report_title or f"Workflow Report {uuid4().hex}",
            "report_item_type_id": resources["report_type_id"],
            "story_ids": list(story_ids),
        },
        "product": {
            "title": product_title or f"Workflow Product {uuid4().hex}",
            "description": "Workflow product description",
            "product_type_id": resources["product_type_id"],
            "default_publisher": resources["publisher_preset_id"],
        },
    }
    if attribute_overrides is not None:
        payload["report"]["attribute_overrides"] = attribute_overrides
    payload["product"].update(product_overrides)
    return payload


class TestAnalyzeApi(BaseTest):
    base_uri = "/api/analyze"

    def test_create_Report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items endpoint to create a report.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "report-items", auth_header=auth_header, json_data=cleanup_report_item)
        assert response.get_json()["report"]["title"] == cleanup_report_item["title"]

    def test_get_Reports(self, client, auth_header, cleanup_report_item):
        """
        GET /api/analyze/report-items endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "report-items", auth_header)
        assert response.get_json()["total_count"] == 1
        items = response.get_json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == cleanup_report_item["title"]

    def test_get_reports_orders_by_story_count(self, client, auth_header, cleanup_report_item, stories, app):
        from core.model.report_item import ReportItem

        unique_suffix = uuid4().hex
        empty_report_id = f"empty-{unique_suffix}"
        linked_report_id = f"linked-{unique_suffix}"

        payloads = [
            {
                "id": empty_report_id,
                "title": f"Story Count Report {unique_suffix}",
                "completed": False,
                "report_item_type_id": cleanup_report_item["report_item_type_id"],
                "stories": [],
            },
            {
                "id": linked_report_id,
                "title": f"Story Count Report {unique_suffix}",
                "completed": False,
                "report_item_type_id": cleanup_report_item["report_item_type_id"],
                "stories": stories[:2],
            },
        ]

        with app.app_context():
            for payload in payloads:
                report_item, status = ReportItem.add(payload)
                assert status == 200
                assert report_item.id == payload["id"]

        try:
            asc_response = self.assert_get_ok(client, f"report-items?search={unique_suffix}&order=stories_asc", auth_header)
            asc_payload = asc_response.get_json()
            assert asc_payload["total_count"] == 2
            assert [item["id"] for item in asc_payload["items"]] == [empty_report_id, linked_report_id]

            desc_response = self.assert_get_ok(client, f"report-items?search={unique_suffix}&order=stories_desc", auth_header)
            desc_payload = desc_response.get_json()
            assert desc_payload["total_count"] == 2
            assert [item["id"] for item in desc_payload["items"]] == [linked_report_id, empty_report_id]
        finally:
            with app.app_context():
                for payload in payloads:
                    if ReportItem.get(payload["id"]):
                        ReportItem.delete(payload["id"])

    def test_get_reports_filters_by_story_id(self, client, auth_header, cleanup_report_item, stories, app):
        from core.model.report_item import ReportItem

        unique_suffix = uuid4().hex
        target_report_id = f"target-{unique_suffix}"
        other_report_id = f"other-{unique_suffix}"

        payloads = [
            {
                "id": target_report_id,
                "title": f"Story Filter Report {unique_suffix}",
                "completed": False,
                "report_item_type_id": cleanup_report_item["report_item_type_id"],
                "stories": [stories[0]],
            },
            {
                "id": other_report_id,
                "title": f"Story Filter Report {unique_suffix}",
                "completed": False,
                "report_item_type_id": cleanup_report_item["report_item_type_id"],
                "stories": [stories[1]],
            },
        ]

        with app.app_context():
            for payload in payloads:
                report_item, status = ReportItem.add(payload)
                assert status == 200
                assert report_item.id == payload["id"]

        try:
            response = self.assert_get_ok(
                client,
                f"report-items?search={unique_suffix}&story_id={stories[0]}",
                auth_header,
            )
            payload = response.get_json()

            assert payload["total_count"] == 1
            assert [item["id"] for item in payload["items"]] == [target_report_id]
            assert payload["items"][0]["stories"] == [stories[0]]
        finally:
            with app.app_context():
                for report_id in (target_report_id, other_report_id):
                    if ReportItem.get(report_id):
                        ReportItem.delete(report_id)

    def test_update_report(self, client, auth_header, cleanup_report_item):
        """
        PUT to /api/analyze/report-items/<report_id> endpoint to update an existing report
        It expects the response to reflect the updated report information
        """
        updated_data = {"title": "Updated Report Title"}
        report_id = cleanup_report_item["id"]
        url = f"report-items/{report_id}"
        response = self.assert_put_ok(client, url, json_data=updated_data, auth_header=auth_header)
        assert response.json["message"] == "Report item updated"
        assert response.json["report"]["title"] == "Updated Report Title"

    def test_clone_report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items/<report_id>/clone endpoint to clone an existing report.
        It expects the response to include the cloned report's details
        """
        from core.model.report_item import ReportItem

        report_id = cleanup_report_item["id"]

        response = self.assert_post_ok(client, f"report-items/{report_id}/clone", {}, auth_header=auth_header)
        assert "id" in response.get_json() and response.get_json()["id"] != report_id, "Cloned report must have a different ID."
        cloned_report = ReportItem.get(response.get_json()["id"])
        assert cloned_report is not None
        assert cloned_report.user_id is not None

    def test_get_report_stories(self, client, auth_header, cleanup_report_item):
        """
        GET /api/analyze/report-items/<report_id>/stories to retrieve stories associated with a report.
        It expects a list of stories in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_get_ok(client, f"report-items/{report_id}/stories", auth_header=auth_header)
        assert response.get_json()["report"]["story_ids"] == [], "The response should be a list of stories."

    def test_update_report_stories(self, client, auth_header, cleanup_report_item, stories):
        """
        PUT to /api/analyze/report-items/<report_id>/stories endpoint to update stories within a report.
        It expects the updated stories to be reflected in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_put_ok(client, f"report-items/{report_id}/stories", json_data=stories, auth_header=auth_header)
        print(response.get_json())
        response_data = response.get_json()

        assert "Successfully updated Report Item" in response_data.get("message"), "The update operation should return a success message."

    def test_delete_report(self, client, auth_header, cleanup_report_item):
        """
        DELETE to /api/analyze/report-items/<report_id> endpoint to remove a report.
        It expects a successful deletion indicated by a 204 No Content status code
        """
        report_id = cleanup_report_item["id"]
        response = self.assert_delete_ok(client, f"report-items/{report_id}", auth_header=auth_header)
        assert "message" in response.text
        assert response.json["message"] == "Successfully deleted report 'Updated Report Title'"

    def test_create_report_with_initial_stories_updates_story_tags_and_relevance(self, app, cleanup_report_item, stories):
        from core.model.report_item import ReportItem
        from core.model.story import Story

        report_payload = deepcopy(cleanup_report_item)
        report_payload["id"] = "report-with-initial-stories"
        report_payload["title"] = "Report With Initial Stories"
        report_payload["stories"] = stories[:2]

        with app.app_context():
            report, status = ReportItem.add(report_payload)
            assert status == 200
            assert report.id == report_payload["id"]

            for story_id in stories[:2]:
                story = Story.get(story_id)
                assert story is not None
                assert any(tag.tag_type == f"report_{report_payload['id']}" for tag in story.tags)
                assert story.relevance_feedback == 3
                assert story.relevance == story.relevance_source + 3 + (story.relevance_override or 0)

    def test_delete_all_reports_cleans_story_tags_and_keeps_stories(self, app, cleanup_report_item, stories):
        from core.model.report_item import ReportItem
        from core.model.story import Story

        report_payload = deepcopy(cleanup_report_item)
        report_payload["id"] = "report-delete-all-cleanup"
        report_payload["title"] = "Report Delete All Cleanup"
        report_payload["stories"] = stories[:1]

        with app.app_context():
            report, status = ReportItem.add(report_payload)
            assert status == 200
            assert report.id == report_payload["id"]

            story_before_delete = Story.get(stories[0])
            assert story_before_delete is not None
            assert story_before_delete.relevance_feedback == 3

            result, delete_status = ReportItem.delete_all()
            assert delete_status == 200
            assert result["message"] == "All ReportItem deleted"

            story_after_delete = Story.get(stories[0])
            assert story_after_delete is not None
            assert all(tag.tag_type != f"report_{report_payload['id']}" for tag in story_after_delete.tags)
            assert story_after_delete.relevance_feedback == 0
            assert story_after_delete.relevance == story_after_delete.relevance_source + (story_after_delete.relevance_override or 0)

    def test_delete_report_keeps_attached_stories(self, app, cleanup_report_item, stories):
        from core.model.report_item import ReportItem
        from core.model.story import Story

        report_payload = deepcopy(cleanup_report_item)
        report_payload["id"] = "report-delete-keeps-stories"
        report_payload["title"] = "Report Delete Keeps Stories"
        report_payload["stories"] = stories[:1]

        with app.app_context():
            report, status = ReportItem.add(report_payload)
            assert status == 200
            assert report.id == report_payload["id"]

            result, delete_status = ReportItem.delete(report.id)
            assert delete_status == 200
            assert result["message"] == "Successfully deleted report 'Report Delete Keeps Stories'"

            story = Story.get(stories[0])
            assert story is not None
            assert all(tag.tag_type != f"report_{report_payload['id']}" for tag in story.tags)
            assert story.relevance_feedback == 0

    def test_create_report_and_publish_product_workflow(self, app, client, auth_header, stories, workflow_publish_resources, monkeypatch):
        from core.model.product import Product
        from core.model.report_item import ReportItem

        scheduled_calls = []

        def fake_autopublish(product_id: str, publisher_id: str):
            scheduled_calls.append((product_id, publisher_id))
            return {"message": "Autopublish scheduled"}, 200

        monkeypatch.setattr("core.service.report_publish_workflow.queue_manager.queue_manager.autopublish_product", fake_autopublish)

        payload = build_publish_product_payload(workflow_publish_resources, stories[:2])
        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)

        assert response.status_code == 201
        response_data = response.get_json()
        report_id = response_data["report"]["id"]
        product_id = response_data["product"]["id"]

        assert response_data["message"] == "Report and product created; publish scheduled"
        assert response_data["product"]["auto_publish"] is True
        assert response_data["product"]["default_publisher"] == workflow_publish_resources["publisher_preset_id"]
        assert response_data["product"]["report_items"] == [report_id]
        assert response_data["publish"]["status"] == "scheduled"
        assert response_data["publish"]["publisher_id"] == workflow_publish_resources["publisher_preset_id"]
        assert scheduled_calls == [(product_id, workflow_publish_resources["publisher_preset_id"])]

        summary_attribute = next(
            attribute
            for attribute in response_data["report"]["attributes"]
            if attribute["title"] == workflow_publish_resources["summary_title"]
        )
        assert summary_attribute["value"] == workflow_publish_resources["summary_default"]
        assert {story["id"] for story in response_data["report"]["stories"]} == set(stories[:2])

        with app.app_context():
            persisted_report = ReportItem.get(report_id)
            persisted_product = Product.get(product_id)
            assert persisted_report is not None
            assert persisted_product is not None
            assert persisted_product.auto_publish is True
            assert [report.id for report in persisted_product.report_items] == [report_id]

    def test_workflow_applies_attribute_overrides(self, client, auth_header, stories, workflow_publish_resources, monkeypatch):
        monkeypatch.setattr(
            "core.service.report_publish_workflow.queue_manager.queue_manager.autopublish_product",
            lambda _product_id, _publisher_id: ({"message": "Autopublish scheduled"}, 200),
        )

        override_value = "Analyst supplied summary"
        payload = build_publish_product_payload(
            workflow_publish_resources,
            stories[:1],
            attribute_overrides=[
                {
                    "group_title": workflow_publish_resources["group_title"],
                    "title": workflow_publish_resources["summary_title"],
                    "value": override_value,
                }
            ],
        )

        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)
        assert response.status_code == 201

        summary_attribute = next(
            attribute
            for attribute in response.get_json()["report"]["attributes"]
            if attribute["title"] == workflow_publish_resources["summary_title"]
        )
        assert summary_attribute["value"] == override_value

    def test_workflow_rejects_ambiguous_attribute_override(self, app, client, auth_header, stories, workflow_publish_resources):
        from core.managers.db_manager import db
        from core.model.attribute import Attribute, AttributeType
        from core.model.report_item_type import AttributeGroupItem, ReportItemType

        duplicate_attribute = None
        duplicate_attribute_id = None
        try:
            with app.app_context():
                duplicate_attribute = Attribute(
                    name=f"workflow_duplicate_{uuid4().hex}",
                    description="Duplicate workflow attribute",
                    attribute_type=AttributeType.STRING,
                    default_value="Default duplicate summary",
                )
                db.session.add(duplicate_attribute)
                db.session.flush()

                report_type = ReportItemType.get(workflow_publish_resources["report_type_id"])
                assert report_type is not None
                report_type.attribute_groups[0].attribute_group_items.append(
                    AttributeGroupItem(
                        title=workflow_publish_resources["summary_title"],
                        description="Duplicate summary field",
                        index=99,
                        attribute_id=duplicate_attribute.id,
                        required=False,
                    )
                )
                db.session.commit()
                duplicate_attribute_id = duplicate_attribute.id

            payload = build_publish_product_payload(
                workflow_publish_resources,
                stories[:1],
                attribute_overrides=[
                    {
                        "group_title": workflow_publish_resources["group_title"],
                        "title": workflow_publish_resources["summary_title"],
                        "value": "Override value",
                    }
                ],
            )

            response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)
            assert response.status_code == 400
            assert "ambiguous" in response.get_json()["error"]
        finally:
            if duplicate_attribute_id is not None:
                with app.app_context():
                    db.session.rollback()
                    report_type = ReportItemType.get(workflow_publish_resources["report_type_id"])
                    if report_type is not None:
                        report_type.attribute_groups[0].attribute_group_items = [
                            item
                            for item in report_type.attribute_groups[0].attribute_group_items
                            if item.attribute_id != duplicate_attribute_id
                        ]
                    if Attribute.get(duplicate_attribute_id):
                        db.session.delete(Attribute.get(duplicate_attribute_id))
                    db.session.commit()

    def test_workflow_rejects_incompatible_product_type(self, app, client, auth_header, stories, workflow_publish_resources):
        from core.managers.db_manager import db
        from core.model.report_item_type import ReportItemType

        incompatible_report_type = None
        incompatible_report_type_id = None
        try:
            with app.app_context():
                incompatible_report_type = ReportItemType(
                    title=f"Incompatible Report Type {uuid4().hex}",
                    description="Incompatible report type for workflow test",
                )
                db.session.add(incompatible_report_type)
                db.session.commit()
                incompatible_report_type_id = incompatible_report_type.id

            payload = build_publish_product_payload(workflow_publish_resources, stories[:1])
            payload["report"]["report_item_type_id"] = incompatible_report_type_id

            response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)
            assert response.status_code == 400
            assert response.get_json()["error"] == "Selected product type does not support the selected report type"
        finally:
            if incompatible_report_type_id is not None:
                with app.app_context():
                    if ReportItemType.get(incompatible_report_type_id):
                        db.session.delete(ReportItemType.get(incompatible_report_type_id))
                        db.session.commit()

    def test_workflow_requires_valid_default_publisher(self, client, auth_header, stories, workflow_publish_resources):
        payload = build_publish_product_payload(workflow_publish_resources, stories[:1], default_publisher="missing-publisher")

        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)
        assert response.status_code == 404
        assert response.get_json()["error"] == "Publisher preset not found"

    def test_workflow_rejects_missing_story_ids(self, app, client, auth_header, stories, workflow_publish_resources):
        from core.model.product import Product
        from core.model.report_item import ReportItem

        payload = build_publish_product_payload(workflow_publish_resources, [stories[0], "missing-story-id"])
        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)

        assert response.status_code == 400
        assert response.get_json()["error"] == "Story ids not found"

        with app.app_context():
            assert Product.get_all_for_collector() == []
            assert ReportItem.get_all_for_collector() == []

    def test_workflow_returns_500_and_keeps_created_items_when_publish_queue_fails(
        self, app, client, auth_header, stories, workflow_publish_resources, monkeypatch
    ):
        from core.model.product import Product
        from core.model.report_item import ReportItem

        monkeypatch.setattr(
            "core.service.report_publish_workflow.queue_manager.queue_manager.autopublish_product",
            lambda _product_id, _publisher_id: ({"error": "Could not schedule autopublish jobs"}, 500),
        )

        payload = build_publish_product_payload(workflow_publish_resources, stories[:1])
        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)

        assert response.status_code == 500
        response_data = response.get_json()
        assert response_data["message"] == "Report and product created; publish scheduling failed"
        assert response_data["publish"]["status"] == "failed"
        assert response_data["publish"]["error"] == "Could not schedule autopublish jobs"

        with app.app_context():
            assert ReportItem.get(response_data["report"]["id"]) is not None
            assert Product.get(response_data["product"]["id"]) is not None

    def test_workflow_requires_all_permissions(self, app, client, auth_header, stories, workflow_publish_resources, monkeypatch):
        from core.model.product import Product
        from core.model.report_item import ReportItem
        from core.model.user import User

        monkeypatch.setattr(User, "get_permissions", lambda _self: ["ANALYZE_CREATE", "PUBLISH_CREATE"])

        payload = build_publish_product_payload(workflow_publish_resources, stories[:1])
        response = client.post(self.concat_url("report-items/publish-product"), json=payload, headers=auth_header)

        assert response.status_code == 403
        assert response.get_json()["error"] == "forbidden"

        with app.app_context():
            assert Product.get_all_for_collector() == []
            assert ReportItem.get_all_for_collector() == []

    def test_get_report_item_passes_current_user_for_acl_check(self, client, auth_header, monkeypatch):
        captured_args: dict[str, object] = {}

        def fake_get_for_api(report_item_id: str, user=None):
            captured_args["report_item_id"] = report_item_id
            captured_args["user"] = user
            return {"id": report_item_id}, 200

        monkeypatch.setattr("core.api.analyze.report_item.ReportItem.get_for_api", fake_get_for_api)

        response = client.get("/api/analyze/report-items/report-1", headers=auth_header)
        assert response.status_code == 200
        assert captured_args["report_item_id"] == "report-1"
        assert captured_args["user"] is not None

    @pytest.mark.parametrize(
        "uri",
        [
            "report-items/report-1/revisions",
            "report-items/report-1/revisions/1",
        ],
    )
    def test_report_revision_endpoints_enforce_read_access(self, client, auth_header, monkeypatch, uri):
        def fake_get_for_api(_report_item_id: str, _user=None):
            return {"error": "forbidden"}, 403

        monkeypatch.setattr("core.api.analyze.report_item.ReportItem.get_for_api", fake_get_for_api)

        response = client.get(self.concat_url(uri), headers=auth_header)
        assert response.status_code == 403
        assert response.get_json() == {"error": "forbidden"}

    def test_hidden_report_type_cannot_be_forged_into_report_creation(self, app, client, auth_header_user_permissions):
        from core.managers.db_manager import db
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType
        from core.model.role import Role
        from core.model.role_based_access import ItemType, RoleBasedAccess

        acl_id = None
        created_report_id = f"forged-report-{uuid4()}"

        visible_before_acl = client.get(self.concat_url("report-types"), headers=auth_header_user_permissions)
        assert visible_before_acl.status_code == 200
        visible_type_ids = [item["id"] for item in visible_before_acl.get_json()["items"]]
        assert visible_type_ids, "Expected at least one report type visible to the non-admin test user"

        with app.app_context():
            admin_role = Role.filter_by_name("Admin")
            assert admin_role is not None
            protected_report_type = ReportItemType.get(visible_type_ids[0])
            assert protected_report_type is not None
            acl = RoleBasedAccess(
                name=f"report-type-acl-{uuid4()}",
                description="Restrict report type to admin role for regression test",
                item_type=ItemType.REPORT_ITEM_TYPE,
                item_id=str(protected_report_type.id),
                roles=[admin_role.id],
                read_only=False,
                enabled=True,
            )
            db.session.add(acl)
            db.session.commit()
            acl_id = acl.id
            protected_report_type_id = protected_report_type.id

        try:
            list_response = client.get(self.concat_url("report-types"), headers=auth_header_user_permissions)
            assert list_response.status_code == 200
            assert protected_report_type_id not in {item["id"] for item in list_response.get_json()["items"]}

            create_response = client.post(
                self.concat_url("report-items"),
                json={
                    "id": created_report_id,
                    "title": "Forged report",
                    "report_item_type_id": protected_report_type_id,
                    "stories": [],
                },
                headers=auth_header_user_permissions,
            )
            assert create_response.status_code == 403
            assert "not allowed to create Report" in create_response.get_json()["error"]
        finally:
            with app.app_context():
                if ReportItem.get(created_report_id):
                    ReportItem.delete(created_report_id)
                if acl_id and RoleBasedAccess.get(acl_id):
                    RoleBasedAccess.delete(acl_id)
