from pyrate_limiter import Any
from tests.functional.helpers import BaseTest


class TestReportActions(BaseTest):
    base_uri = "/api/analyze"

    def test_report_item_actions(self, client, session, cleanup_report_item, auth_header):
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


class TestReportHistory(BaseTest):
    base_uri = "/api/analyze"

    def test_report_history_creation(self, client, session, logger, input_report: dict[str, Any], auth_header):
        from core.model.report_item import ReportItem

        report_item, code = ReportItem.add(input_report, user=None)

        assert code == 200
        assert report_item.id
        assert report_item.title == input_report["title"]
        ReportItemHistory = ReportItem.__history_mapper__.class_
        assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 0, "Initial version should not be created"

        report_item.update({"title": "Updated Report Title"})
        import pdb

        pdb.set_trace()
        logger.debug(f"{session.query(ReportItemHistory).all()=}")
        assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 1, "First version should be created"
        assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).first().title == "Updated Report Title"

    def test_report_history_creation_with_story_updates(self, client, logger, input_report: dict[str, Any], stories, auth_header):
        # create a report item, add a story based on the IDs from fixture stories and exptect the history to be created
        from core.model.report_item import ReportItem

        report_item, code = ReportItem.add(input_report, user=None)
        assert code == 200
        assert report_item.id
        assert report_item.title == input_report["title"]
        # ReportItemHistory = ReportItem.__history_mapper__.class_
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 0, "Initial version should not be created"
        report_item.update({"title": "Updated Report Title"})
        # logger.debug(f"{session.query(ReportItemHistory).all()=}")
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).count() == 1, "First version should be created"
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.version == 1).first().title == "Test Report"
        report_item.update({"stories": stories})
        # assert session.query(ReportItemHistory).all() == 2, "Second version should be created"
        # Verify that the story is linked to the report item
        assert stories[0].id in report_item.stories, f"Story {stories[0].id} should be linked to the report item {report_item.id}"
        from core.model.story import Story

        # Verify that the report item is linked to the story
        story = Story.get(stories[0].id)
        assert report_item.id in story.report_items, f"Report item {report_item.id} should be linked to the story {stories[0].id}"
        # Verify that the history entry is created for the story
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).count() == 1, (
        #     "History entry should be created for the report item"
        # )
        # assert session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).first().title == "Updated Report Title", (
        #     "History entry title should match the updated report item title"
        # )

    #
    def test_report_multiple_updates_history(self, client, session, logger, input_report: dict[str, Any], auth_header):
        """Test that multiple report item updates create correct version history with incremental version numbers"""
        from core.model.report_item import ReportItem

        # Add initial report
        report_item, code = ReportItem.add(input_report, user=None)
        assert code == 200, f"Expected status code 200, got {code}"
        assert report_item.id
        assert report_item.title == input_report["title"]

        ReportItemHistory = ReportItem.__history_mapper__.class_

        # Expect no history yet (assuming first insert does not version)
        initial_history_count = session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).count()
        assert initial_history_count == 0, f"Expected no history after insert, got {initial_history_count}"

        # First update
        report_item.update({"title": "First Update Title", "summary": "First summary"})
        # Second update
        report_item.update({"title": "Second Update Title", "summary": "Second summary"})
        # Third update
        report_item.update({"title": "Third Update Title", "summary": "Third summary"})

        # Verify history entries
        all_history = (
            session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id).order_by(ReportItemHistory.version).all()
        )

        assert len(all_history) == 3, f"Expected 3 versions, got {len(all_history)}"

        expected_titles = ["Test Report", "First Update Title", "Second Update Title"]

        for version, expected_title in enumerate(expected_titles, start=1):
            entry = (
                session.query(ReportItemHistory).filter(ReportItemHistory.id == report_item.id, ReportItemHistory.version == version).first()
            )
            assert entry is not None, f"Version {version} entry not found"
            assert entry.title == expected_title, f"Version {version} title mismatch: expected '{expected_title}', got '{entry.title}'"

        # Verify final state
        current_report = ReportItem.get(report_item.id)
        assert current_report.title == "Third Update Title", (
            f"Final title mismatch: expected 'Third Update Title', got '{current_report.title}'"
        )
