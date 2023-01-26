import json
import requests
import base64
from bots.managers.log_manager import logger
from bots.config import Config


class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_NG_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = self.get_headers()
        self.node_id = self.get_node_id()

    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def get_node_id(self) -> str:
        uid = self.api_url + self.api_key
        return base64.urlsafe_b64encode(uid.encode("utf-8")).decode("utf-8")

    def register_node(self, bots_info):
        try:
            response, status = self.get_bot_node_status()
            if status == 200:
                return response, status
            node_info = {
                "id": self.node_id,
                "name": Config.NODE_NAME,
                "description": Config.NODE_DESCRIPTION,
                "api_url": Config.NODE_URL,
                "api_key": Config.API_KEY,
                "bots_info": bots_info,
            }
            response = requests.post(
                f"{self.api_url}/api/v1/bots/node",
                json=node_info,
                headers=self.headers,
            )

            if response.status_code != 200:
                logger.log_debug(f"Can't register Bot node: {response.text}")
                return None, 400

            return response.json(), response.status_code
        except Exception as e:
            logger.log_debug("Can't register Bot node")
            logger.log_debug(str(e))
            return None, 400

    def get_bot_node_status(self):
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/{self.node_id}",
                headers=self.headers,
            )

            return response.json(), response.status_code
        except Exception:
            logger.log_debug_trace("Cannot update Bot status")
            return None, 400

    def get_bots_presets(self, bot_type):
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/bots/bots-presets",
                json={"api_key": self.api_key, "bot_type": bot_type},
                headers=self.headers,
            )
            return response.json(), response.status_code
        except (requests.exceptions.ConnectionError, json.decoder.JSONDecodeError):
            return {}, 503

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

    def update_news_items_aggregate_summary(self, id, summary):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-items-aggregate/{id}/summary",
                json=summary,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            logger.log_debug_trace("update_news_items_aggregate_summary failed")
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
                f"{self.api_url}/api/v1/bots/news-item-aggregates-group-action",
                json=data,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None, 400
