import requests
import base64
import hashlib
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
        uid = Config.NODE_URL + Config.API_KEY + Config.NODE_NAME + Config.TARANIS_NG_CORE_URL
        return hashlib.md5(uid.encode("utf-8")).hexdigest()

    def register_node(self):
        try:
            response = self.get_bot_node_status()
            if response:
                logger.log_info(f"Found registerd Bot {response}")
                return

            logger.log_info(f"Registering bot Node at {Config.TARANIS_NG_CORE_URL}")
            node_info = {
                "id": self.node_id,
                "name": Config.NODE_NAME,
                "description": Config.NODE_DESCRIPTION,
                "api_url": Config.NODE_URL,
                "api_key": Config.API_KEY,
            }
            response = requests.post(
                f"{self.api_url}/api/v1/bots/node",
                json=node_info,
                headers=self.headers,
            )

            if response.ok:
                logger.log_info(f"Successfully registered: {response}")
            else:
                logger.critical(f"Can't register Bot node: {response.text}")

        except Exception:
            logger.log_debug_trace("Can't register Bot node")
            return None

    def get_bot_node_status(self) -> dict | None:
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/node/{self.node_id}",
                headers=self.headers,
            )

            return response.json() if response.ok else None
        except Exception:
            logger.log_debug_trace("Cannot update Bot status")
            return None

    def get_bots(self) -> dict | None:
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots",
                headers=self.headers,
            )
            return response.json()["items"] if response.ok else None
        except Exception:
            logger.log_debug_trace("Can't get Bot infos")
            return None

    def get_news_items_data(self, limit) -> dict | None:
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/bots/news-item-data?limit={limit}",
                headers=self.headers,
            )
            return response.json() if response.ok else None
        except Exception:
            return None

    def update_news_item_data(self, id, data) -> int:
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-item-data/{id}",
                json=data,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return 400

    def update_news_item_attributes(self, id, attributes) -> int:
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-item-data/{id}/attributes",
                json=attributes,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return 400

    def update_news_item_tags(self, id, tags) -> int:
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/bots/news-items-aggregate/{id}/tags",
                json=tags,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            logger.log_debug_trace("update_news_item_tags failed")
            return 400

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

    def get_news_items_aggregate(self, source_group: str | None, limit: str | None) -> dict | None:
        try:
            uri = (
                f"{self.api_url}/api/v1/bots/news-item-aggregates-by-group/{source_group}"
                if source_group
                else f"{self.api_url}/api/v1/bots/news-item-aggregates"
            )
            response = requests.get(
                uri,
                headers=self.headers,
            )
            return response.json() if response.ok else None
        except Exception:
            logger.log_debug_trace("get_news_items_aggregate failed")
            return None

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
