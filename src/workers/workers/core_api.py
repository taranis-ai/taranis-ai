import requests
from workers.log import logger
from workers.config import get_settings


class CoreApi:
    def __init__(self):
        config = get_settings()
        self.api_url = config.TARANIS_NG_CORE_URL
        self.api_key = config.API_KEY
        self.headers = self.get_headers()

    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def get_news_items_data(self, limit):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/news-item-data?limit={limit}",
                headers=self.headers,
            )
            return response.json()
        except Exception:
            return None, 400

    def update_news_item_attributes(self, id, attributes):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-item-data/{id}/attributes",
                json=attributes,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    def update_news_item_tags(self, id, tags):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-item-data/{id}/tags",
                json=tags,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            logger.log_debug_trace("update_news_item_tags failed")
            return None, 400

    def delete_word_list_category_entries(self, id, name):
        try:
            response = requests.delete(
                f"{self.api_url}/api/v1/bots/word-list-categories/{id}/entries/{name}",
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    def update_word_list_category_entries(self, id, name, entries):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/word-list-categories/{id}/entries/{name}",
                json=entries,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    def get_categories(self, id):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/word-list-categories/{id}",
                headers=self.headers,
            )
            return response.json()
        except Exception:
            return None, 400

    def add_word_list_category(self, id, category):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/word-list-categories/{id}",
                json=category,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400

    def get_news_items_aggregate(self, source_group, limit):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/news-item-aggregates-by-group/{source_group}",
                headers=self.headers,
            )
            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("get_news_items_aggregate failed")
            return None, 400

    def news_items_grouping(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-item-aggregates/group",
                json=data,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400
