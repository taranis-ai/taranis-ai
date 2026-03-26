from copy import deepcopy

import pytest

from tests.functional.helpers import BaseTest


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
