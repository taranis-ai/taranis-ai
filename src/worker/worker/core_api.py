from urllib.parse import urlencode

import requests

from worker.config import Config
from worker.log import logger
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

    def get_all_osint_sources(self) -> list[dict] | None:
        """Get all OSINT sources from the Core API.

        Returns:
            List of source dictionaries, or None if the request fails
        """
        try:
            response = self.api_get("/worker/osint-sources")
            if response and "sources" in response:
                return response["sources"]
            return None
        except Exception:
            logger.exception("Can't get all OSINT sources")
            return None

    def get_all_bots(self) -> list[dict] | None:
        """Get all bots from the Core API.

        Returns:
            List of bot dictionaries, or None if the request fails
        """
        try:
            response = self.api_get("/worker/bots")
            # API returns {"items": [...]} format
            if response and isinstance(response, dict) and "items" in response:
                return response["items"]
            # Fallback for direct list format (backwards compatibility)
            if response and isinstance(response, list):
                return response
            return None
        except Exception:
            logger.exception("Can't get all bots")
            return None

    def get_cron_jobs(self) -> list[dict] | None:
        """Get all cron job configurations from the Core API.

        Returns:
            List of cron job configurations, or None if the request fails
        """
        try:
            response = self.api_get("/api/config/workers/cron-jobs")
            if response and "cron_jobs" in response:
                return response["cron_jobs"]
            return None
        except Exception:
            logger.exception("Can't get cron job configurations")
            return None

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

    def get_product(self, product_id: str) -> dict | None:
        return self.api_get(f"/worker/products/{product_id}")

    def get_product_render(self, product_id: str) -> Product | None:
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

    def update_word_list(self, word_list_id: int, content: str | dict | list, content_type: str) -> dict | None:
        """Update a word list with new content.

        Args:
            word_list_id: ID of the word list to update
            content: The content to upload (text/csv string or json list/dict)
            content_type: MIME type of the content ('text/csv' or 'application/json')

        Returns:
            Response from the API or None on failure
        """
        try:
            url = f"{self.api_url}/worker/word-list/{word_list_id}"
            headers = {**self.headers, "Content-Type": content_type}

            if content_type == "application/json":
                response = requests.put(url=url, headers=headers, json=content, verify=self.verify, timeout=self.timeout)
            elif content_type == "text/csv":
                response = requests.put(
                    url=url,
                    headers=headers,
                    data=content.encode("utf-8") if isinstance(content, str) else content,
                    verify=self.verify,
                    timeout=self.timeout,
                )
            else:
                logger.error(f"Unsupported content type: {content_type}")
                return None

            return self.check_response(response, url)
        except Exception as e:
            logger.exception(f"Failed to update word list {word_list_id}: {e}")
            return None

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

    def run_post_collection_bots(self, source_id) -> dict | None:
        try:
            return self.api_put("/worker/post-collection-bots", json_data={"source_id": source_id})
        except Exception:
            logger.exception("Can't run Post Collection Bots")
            return None

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

    def add_news_items(self, news_items) -> dict | None:
        try:
            return self.api_post(url="/worker/news-items", json_data=news_items)
        except Exception:
            logger.exception("Cannot add Newsitem")
            return None

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

    def add_or_update_for_misp(self, stories: list[dict]):
        """
        Add or update a story for MISP.
        """
        try:
            return self.api_post(
                url="/worker/stories/misp",
                json_data=stories,
            )
        except Exception:
            logger.exception("Cannot add or update story.")
            return None
