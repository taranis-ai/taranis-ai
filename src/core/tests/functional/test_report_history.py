from pyrate_limiter import Any
from tests.functional.helpers import BaseTest


class TestReportActions(BaseTest):
    base_uri = "/api/analyze"

    def test_report_item_actions(self, client, db_global_session, cleanup_report_item, auth_header):
        report_item: dict = cleanup_report_item
        response = self.assert_post_ok(client, "report-items", json_data=report_item, auth_header=auth_header)
        assert response.get_json()["title"] == report_item["title"]
        report_item_id = response.get_json()["id"]
        assert report_item_id

        # Update the report item
        updated_data = {"title": "Updated Report Title"}
        response = self.assert_put_ok(client, f"report-items/{report_item_id}", json_data=updated_data, auth_header=auth_header)
        assert response.json["message"] == "Successfully updated Report Item"

        response = self.assert_get_ok(client, f"report-items/{report_item_id}", auth_header=auth_header)
        assert response.json["title"] == updated_data["title"]

        # Delete the report item
        response = self.assert_delete_ok(client, f"report-items/{report_item_id}", auth_header=auth_header)
        assert response.json["message"] == "Report successfully deleted"


class TestReportHistory(BaseTest):
    """Test class of chained test cases reusing the same report item"""

    base_uri = "/api/analyze"

    def test_report_history_creation(self, client, db_global_session, logger, input_report: dict[str, Any], auth_header):
        from core.model.report_item import ReportItem

        report_item, code = ReportItem.add(input_report, user=None)

        assert code == 200
        assert report_item.id
        assert report_item.title == input_report["title"]
        ReportItemHistory = ReportItem.__history_mapper__.class_
        assert db_global_session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 0, (
            "Initial version should not be created"
        )

        report_item.update({"title": "Updated Report Title"})
        logger.debug(f"{db_global_session.query(ReportItemHistory).all()=}")
        assert db_global_session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 1, (
            "First version should be created"
        )
        assert db_global_session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).first().title == "Test Report"

    def test_report_history_creation_with_story_updates(
        self, client, db_global_session, logger, input_report: dict[str, Any], stories, auth_header
    ):
        # create a report item, add a story based on the IDs from fixture stories and exptect the history to be created
        from core.model.report_item import ReportItem

        # report_item, code = ReportItem.add(input_report, user=None)
        # assert code == 200
        # assert report_item.id
        # assert report_item.title == input_report["title"]
        # ReportItemHistory = ReportItem.__history_mapper__.class_
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 0, "Initial version should not be created"
        report_item = ReportItem.get("42")
        report_item.title = "Updated Report Title"
        # logger.debug(f"{session.query(ReportItemHistory).all()=}")
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 1, "First version should be created"
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).first().title == "Test Report"
        report_item.update_stories(stories)
        # assert session.query(ReportItemHistory).all() == 2, "Second version should be created"
        # Verify that the story is linked to the report item
        # import pdb; pdb.set_trace()
        story_ids_from_report = [story.id for story in report_item.stories]
        assert stories[0] in story_ids_from_report
        assert stories[1] in story_ids_from_report

        from core.model.story import Story

        # Verify that the report item is linked to the story
        story = Story.get(stories[0])
        assert story.tags[0].tag_type == f"report_{report_item.id}"
        # Verify that the history entry is created for the story
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).count() == 1, (
        #     "History entry should be created for the report item"
        # )
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).first().title == "Updated Report Title", (
        #     "History entry title should match the updated report item title"
        # )
