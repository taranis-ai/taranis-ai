from unittest.mock import Mock
from core.model.role import TLPLevel
from core.managers.db_manager import db


class TestRBAC:
    def test_filter_report_query_with_tlp(self, report_items):
        from core.model.report_item import ReportItem
        from core.service.role_based_access import RoleBasedAccessService

        item1, item2, item3 = report_items

        mock_user = Mock()

        # User has TLP:Green -> Should see only Report Item with TLP:Clear
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        query = ReportItem.query
        results = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user).all()

        result_ids = {r.id for r in results}
        assert item1.id in result_ids
        assert item2.id not in result_ids
        assert item3.id not in result_ids

        # User has TLP:Amber -> Should see Report Items with TLP:Clear & TLP:Amber
        mock_user.get_highest_tlp.return_value = TLPLevel.AMBER
        query = ReportItem.query
        results = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user).all()
        result_ids = {r.id for r in results}
        assert item1.id in result_ids
        assert item2.id in result_ids
        assert item3.id not in result_ids

        # User has TLP:Red -> Should see all Report Items
        mock_user.get_highest_tlp.return_value = TLPLevel.RED
        query = ReportItem.query
        results = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user).all()
        result_ids = {r.id for r in results}
        assert item1.id in result_ids
        assert item2.id in result_ids
        assert item3.id in result_ids

        # User has no TLP level set -> Should see all Report Items
        mock_user.get_highest_tlp.return_value = None
        query = ReportItem.query
        results = RoleBasedAccessService.filter_report_query_with_tlp(query, mock_user).all()
        result_ids = {r.id for r in results}
        assert item1.id in result_ids
        assert item2.id in result_ids
        assert item3.id in result_ids
        db.session.remove()

    def test_filter_query_with_tlp(self, stories_with_tlp):
        from core.model.story import Story
        from core.service.role_based_access import RoleBasedAccessService

        mock_user = Mock()

        # User has only TLP level Clear -> lowest Story TLP level is Green -> empty set
        mock_user.get_highest_tlp.return_value = TLPLevel.CLEAR
        results = RoleBasedAccessService.filter_query_with_tlp(Story.query, mock_user).all()
        assert results == []

        # User has TLP level Green -> should see the TLP Green story
        mock_user.get_highest_tlp.return_value = TLPLevel.GREEN
        results = RoleBasedAccessService.filter_query_with_tlp(Story.query, mock_user).all()
        result_ids = {story.id for story in results}
        assert stories_with_tlp[0] in result_ids
        assert stories_with_tlp[1] not in result_ids

        # User has TLP level Red -> should see all stories
        mock_user.get_highest_tlp.return_value = TLPLevel.RED
        results = RoleBasedAccessService.filter_query_with_tlp(Story.query, mock_user).all()
        result_ids = {story.id for story in results}
        assert stories_with_tlp[0] in result_ids
        assert stories_with_tlp[1] in result_ids

        # User has no TLP level -> should see all stories
        mock_user.get_highest_tlp.return_value = None
        results = RoleBasedAccessService.filter_query_with_tlp(Story.query, mock_user).all()
        result_ids = {story.id for story in results}
        assert stories_with_tlp[0] in result_ids
        assert stories_with_tlp[1] in result_ids

        db.session.remove()
