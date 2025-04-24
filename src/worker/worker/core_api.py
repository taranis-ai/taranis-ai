import requests
from urllib.parse import urlencode

from worker.log import logger
from worker.config import Config
from worker.types import Product


class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION
        self.timeout = Config.REQUESTS_TIMEOUT

    def get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def check_response(self, response: requests.Response, url: str):
        try:
            if response.ok:
                return response.json()
        except Exception:
            logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        return None

    def api_put(self, url: str, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.put(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)
        return self.check_response(response, url)

    def api_patch(self, url, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.patch(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)
        return self.check_response(response, url)

    def api_post(self, url, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.post(url=url, headers=self.headers, verify=self.verify, json=json_data, timeout=self.timeout)
        return self.check_response(response, url)

    def api_get(self, url: str, params=None):
        url = f"{self.api_url}{url}"
        if params:
            url += f"?{urlencode(params)}"
        response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        return self.check_response(response, url)

    def api_delete(self, url: str):
        url = f"{self.api_url}{url}"
        response = requests.delete(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        return self.check_response(response, url)

    def get_bot_config(self, bot_id: str) -> dict | None:
        try:
            return self.api_get(f"/worker/bots/{bot_id}")
        except Exception:
            logger.exception("Can't get Bot Config")
            return None

    def get_osint_source(self, source_id: str) -> dict | None:
        return self.api_get(f"/worker/osint-sources/{source_id}")

    def get_connector_config(self, connector_id: str) -> dict | None:
        return self.api_get(f"/worker/connectors/{connector_id}")

    def get_product(self, product_id: int) -> dict | None:
        return self.api_get(f"/worker/products/{product_id}")

    def get_product_render(self, product_id: int) -> Product | None:
        try:
            url = f"{self.api_url}/worker/products/{product_id}/render"
            response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
            if not response.ok:
                logger.error(f"Call to {url} failed {response.status_code}")
                return None
            return Product(response)
        except Exception:
            logger.exception("Can't get Product Render")
            return None

    def get_publisher(self, publisher_id: str) -> dict | None:
        return self.api_get(f"/worker/publishers/{publisher_id}")

    def get_template(self, presenter: int) -> str | None:
        url = f"{self.api_url}/worker/presenters/{presenter}"
        response = requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        return response.text if response.ok else None

    def get_word_list(self, word_list_id: int) -> dict | None:
        return self.api_get(
            url=f"/worker/word-list/{word_list_id}",
        )

    def get_news_items(self, limit) -> dict | None:
        try:
            return self.api_get("/bots/news-item", params={"limit": limit})
        except Exception:
            return None

    def get_stories(self, filter_dict: dict) -> list | None:
        return self.api_get("/worker/stories", params=filter_dict) or []

    def get_tags(self) -> dict | None:
        return self.api_get("/worker/tags")

    def get_words_for_tagging_bot(self) -> dict | None:
        try:
            return self.api_get(url="/worker/word-lists?usage=4&with_entries=true")
        except Exception:
            return None

    def update_news_item(self, news_id: str, data) -> dict | None:
        try:
            return self.api_put(url=f"/bots/news-item/{news_id}", json_data=data)
        except Exception:
            return None

    def update_story_summary(self, story_id, summary: str) -> dict | None:
        try:
            data = {"summary": summary}
            return self.api_put(url=f"/bots/story/{story_id}", json_data=data)
        except Exception:
            return None

    def update_news_item_attributes(self, news_id: str, attributes) -> dict | None:
        try:
            return self.api_put(url=f"/bots/news-item/{news_id}/attributes", json_data=attributes)
        except Exception:
            return None

    def update_story_attributes(self, story_id: str, attributes: list[dict]) -> dict | None:
        """Patch story attributes

        Example:

        update_story_attributes("story_id", [{"key": "key1", "value": "value1"}, {"key": "key2", "value": "value2"}])

        """
        try:
            return self.api_patch(url=f"/bots/story/{story_id}/attributes", json_data=attributes)
        except Exception:
            return None

    def update_tags(self, tags, bot_type) -> dict | None:
        try:
            if tags:
                return self.api_put(url=f"/worker/tags?bot_type={bot_type}", json_data=tags)
        except Exception:
            logger.exception("update_tags failed")
            return None

    def run_post_collection_bots(self, source_id) -> dict | None:
        try:
            return self.api_put("/worker/post-collection-bots", json_data={"source_id": source_id})
        except Exception:
            logger.exception("Can't run Post Collection Bots")
            return None

    def update_osintsource_status(self, osint_source_id: str, error_msg: dict | None = None) -> dict | None:
        return self.api_put(url=f"/worker/osint-sources/{osint_source_id}", json_data=error_msg)

    def update_osint_source_icon(self, osint_source_id: str, icon) -> dict | None:
        try:
            url = f"{self.api_url}/worker/osint-sources/{osint_source_id}/icon"
            headers = self.headers.copy()
            headers.pop("Content-type", None)
            return self.check_response(requests.put(url=url, files=icon, headers=headers, verify=self.verify, timeout=self.timeout), url)
        except Exception:
            return None

    def news_items_grouping(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/bots/stories/group",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
            )
            return response.status_code
        except Exception:
            return None

    def news_items_grouping_multiple(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/bots/stories/group-multiple",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
            )
            return response.status_code
        except Exception:
            return None

    def add_news_items(self, news_items) -> dict | bool | None:
        try:
            return self.api_post(url="/worker/news-items", json_data=news_items)
        except Exception:
            logger.exception("Cannot add Newsitem")
            return False

    def add_or_update_story(self, story: dict):
        """
        Add or update a story.
        If a story has a conflict flag, you might route it to a separate endpoint.
        """
        try:
            return self.api_post(
                url="/worker/stories",
                json_data=story,
            )
        except Exception:
            logger.exception("Cannot add or update story.")
            return None

    def store_task_result(self, data) -> dict | None:
        try:
            return self.api_post(url="/tasks/", json_data=data)
        except Exception:
            logger.exception("Cannot store task result")
            return None

    def get_task(self, task_id) -> requests.Response:
        try:
            url = f"{self.api_url}/tasks/{task_id}"
            return requests.get(url=url, headers=self.headers, verify=self.verify, timeout=self.timeout)
        except Exception as e:
            raise e
