from unittest.mock import Mock
from core.model.role import TLPLevel
from core.managers.db_manager import db


class TestRBAC:
    def test_filter_report_query_with_tlp(self, report_items):
        from core.model.report_item import ReportItem
        from core.service.role_based_access import RoleBasedAccessService

        item1, item2, item3 = report_items

        mock_user = Mock()
        query = db.select(ReportItem)

        # User has TLP:Green -> Should see only Report Item with TLP:Clear
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results

        result_ids = {r.id for r in results}
        assert {item1.id} == result_ids

        # User has TLP:Amber -> Should see Report Items with TLP:Clear & TLP:Amber
        mock_user.get_highest_tlp.return_value = TLPLevel.AMBER
        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results
        result_ids = {r.id for r in results}
        assert {item1.id, item2.id} == result_ids

        # User has TLP:Red -> Should see all Report Items
        mock_user.get_highest_tlp.return_value = TLPLevel.RED

        filter_query = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user)
        results = ReportItem.get_filtered(filter_query)
        assert results
        result_ids = {r.id for r in results}
        assert {item1.id, item2.id, item3.id} == result_ids

    def test_filter_query_with_tlp(self, stories_with_tlp):
        from core.model.story import Story
        from core.service.role_based_access import RoleBasedAccessService

        mock_user = Mock()
        query = db.select(Story)

        # User has only TLP level Clear -> lowest Story TLP level is Green -> empty set
        mock_user.get_highest_tlp.return_value = TLPLevel.CLEAR
        filter_query = RoleBasedAccessService.filter_query_with_tlp(query, mock_user)
        results = Story.get_filtered(filter_query)
        assert results
        result_ids = {n.id for story in results for n in story.news_items}
        assert result_ids == {"tlp-news-clear"}

        # User has TLP level Green -> should see the TLP Green story
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
