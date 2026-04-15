from unittest.mock import Mock

from core.managers.db_manager import db
from core.model.role import TLPLevel


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
        assert read_error == {"error": f"User {clear_user.id} is not allowed to read Report {report_item_amber.id}"}

        blocked_report, update_error, update_status = ReportItem.get_report_item_and_check_permission(report_item_amber.id, clear_user)
        assert blocked_report is None
        assert update_status == 403
        assert update_error == {"error": f"User {clear_user.id} is not allowed to update Report {report_item_amber.id}"}

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
        result_ids = {n.id for story in results for n in story.news_items}
        assert result_ids == {"tlp-news-clear"}

        # User has TLP level Green -> should see the TLP Green and Clear story
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_ids = {n.id for story in results for n in story.news_items}
        assert result_ids == {"tlp-news-green", "tlp-news-clear"}

        # User has TLP level Red -> should see all stories
        mock_user.get_highest_tlp.return_value = TLPLevel.RED
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_ids = {n.id for story in results for n in story.news_items}
        assert result_ids == {"tlp-news-green", "tlp-news-clear", "tlp-news-red"}

        db.session.remove()
