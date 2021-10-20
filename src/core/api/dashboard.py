from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource

from managers import log_manager
from model.news_item import NewsItemData
from model.product import Product
from model.report_item import ReportItem
from model.tag_cloud import TagCloud


class Dashboard(Resource):

    @jwt_required
    def get(self):

        try:
            tag_cloud_day = 0
            if 'tag_cloud_day' in request.args and request.args['tag_cloud_day']:
                tag_cloud_day = min(int(request.args['tag_cloud_days']), 7)
        except Exception as ex:
            log_manager.debug_log(ex)
            return "", 400

        total_news_items = NewsItemData.count_all()
        total_products = Product.count_all()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        total_database_items = total_news_items + total_products + report_items_completed + report_items_in_progress
        latest_collected = NewsItemData.latest_collected()
        grouped_words = TagCloud.get_grouped_words(tag_cloud_day)
        return {'total_news_items': total_news_items, 'total_products': total_products,
                'report_items_completed': report_items_completed, 'report_items_in_progress': report_items_in_progress,
                'total_database_items': total_database_items, 'latest_collected': latest_collected,
                'tag_cloud': grouped_words}


def initialize(api):
    api.add_resource(Dashboard, "/api/v1/dashboard-data")
