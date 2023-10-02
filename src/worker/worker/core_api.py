import requests
from urllib.parse import urlencode

from worker.log import logger
from worker.config import Config


class CoreApi:
    def __init__(self):
        self.api_url = Config.TARANIS_NG_CORE_URL
        self.api_key = Config.API_KEY
        self.headers = self.get_headers()
        self.verify = Config.SSL_VERIFICATION

    def get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-type": "application/json"}

    def check_response(self, response, url):
        try:
            if response.ok:
                return response.json()
        except Exception:
            logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        logger.error(f"Call to {url} failed {response.status_code}: {response.text}")
        return None

    def api_put(self, url, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.put(url=url, headers=self.headers, verify=self.verify, json=json_data)
        return self.check_response(response, url)

    def api_post(self, url, json_data=None):
        url = f"{self.api_url}{url}"
        if not json_data:
            json_data = {}
        response = requests.post(url=url, headers=self.headers, verify=self.verify, json=json_data)
        return self.check_response(response, url)

    def api_get(self, url, params=None):
        url = f"{self.api_url}{url}"
        if params:
            url += f"?{urlencode(params)}"
        response = requests.get(url=url, headers=self.headers, verify=self.verify)
        return self.check_response(response, url)

    def api_delete(self, url):
        url = f"{self.api_url}{url}"
        response = requests.delete(url=url, headers=self.headers, verify=self.verify)
        return self.check_response(response, url)

    def get_post_collection_bots_config(self) -> list[dict] | None:
        try:
            return self.api_get("/worker/post-collection-bots")
        except Exception:
            logger.log_debug_trace("Can't get Bots Config")
            return None

    def get_bot_config(self, bot_id: str) -> dict | None:
        try:
            return self.api_get(f"/worker/bots/{bot_id}")
        except Exception:
            logger.log_debug_trace("Can't get Bot Config")
            return None

    def get_osint_source(self, source_id: str) -> dict | None:
        return self.api_get(f"/worker/osint-sources/{source_id}")

    def get_product(self, product_id: int) -> dict | None:
        return self.api_get(f"/worker/products/{product_id}")

    def get_template(self, presenter: int) -> str | None:
        url = f"{self.api_url}/worker/presenters/{presenter}"
        response = requests.get(url=url, headers=self.headers, verify=self.verify)
        return response.text if response.ok else None

    def upload_rendered_product(self, product_id, product) -> dict | None:
        url = f"{self.api_url}/worker/products/{product_id}"
        headers = self.headers.copy()
        headers["Content-type"] = product["mime_type"]
        return self.check_response(requests.put(url=url, data=product["data"], headers=headers, verify=self.verify), url)

    def get_schedule(self) -> dict | None:
        try:
            return self.api_get(url="/beat/schedule")
        except Exception:
            return None

    def get_word_list(self, word_list_id: int) -> dict | None:
        try:
            return self.api_get(
                url=f"/worker/word-list/{word_list_id}",
            )
        except Exception:
            return None

    def get_news_items_data(self, limit) -> dict | None:
        try:
            return self.api_get("/bots/news-item-data", params={"limit": limit})
        except Exception:
            return None

    def get_news_items_aggregate(self, filter_dict: dict) -> list:
        try:
            return self.api_get("/worker/news-item-aggregates", params=filter_dict) or []
        except Exception:
            logger.log_debug_trace("get_news_items_aggregate failed")
            return []

    def get_tags(self) -> dict | None:
        return self.api_get("/worker/tags")

    def get_words_for_tagging_bot(self) -> dict | None:
        try:
            return self.api_get(url="/worker/word-lists?usage=4")
        except Exception:
            return None

    def update_news_item_data(self, id, data) -> dict | None:
        try:
            return self.api_put(url=f"/bots/news-item-data/{id}", json_data=data)
        except Exception:
            return None

    def update_news_items_aggregate_summary(self, id, summary) -> dict | None:
        try:
            return self.api_put(url=f"/bots/aggregate/{id}/summary", json_data=summary)
        except Exception:
            return None

    def update_schedule(self, schedule) -> dict | None:
        try:
            return self.api_put(url="/beat/schedule", json_data=schedule)
        except Exception:
            return None

    def update_news_item_attributes(self, id, attributes) -> dict | None:
        try:
            return self.api_put(url=f"/bots/news-item-data/{id}/attributes", json_data=attributes)
        except Exception:
            return None

    def update_tags(self, tags, bot_type) -> dict | None:
        try:
            if tags:
                return self.api_put(url=f"/worker/tags?bot_type={bot_type}", json_data=tags)
        except Exception:
            logger.log_debug_trace("update_tags failed")
            return None

    def update_word_list(self, word_list_id, content, content_type) -> dict | None:
        try:
            url = f"{self.api_url}/worker/word-list/{word_list_id}/update"
            headers = self.headers.copy()
            headers["Content-type"] = content_type
            # url = "http://127.0.0.1:8888/anything"
            if content_type == "text/csv":
                return self.check_response(requests.put(url=url, data=content, headers=headers, verify=self.verify), url)
            elif content_type == "application/json":
                return self.check_response(requests.put(url=url, json=content, headers=headers, verify=self.verify), url)
        except Exception:
            return None

    def update_osintsource_status(self, osint_source_id: str, error_msg: dict | None = None) -> dict | None:
        return self.api_put(url=f"/worker/osint-sources/{osint_source_id}", json_data=error_msg)

    def update_osint_source_icon(self, osint_source_id: str, icon) -> dict | None:
        try:
            url = f"{self.api_url}/worker/osint-sources/{osint_source_id}/icon"
            headers = self.headers.copy()
            headers.pop("Content-type", None)
            return self.check_response(requests.put(url=url, files=icon, headers=headers, verify=self.verify), url)
        except Exception:
            return None

    def update_next_run_time(self, next_run_times: dict) -> dict | None:
        try:
            return self.api_put(url="/beat/next-run-time", json_data=next_run_times)
        except Exception:
            return None

    def news_items_grouping(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/bots/news-item-aggregates/group",
                json=data,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None

    def news_items_grouping_multiple(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/bots/news-item-aggregates/group-multiple",
                json=data,
                headers=self.headers,
            )
            return response.status_code
        except Exception:
            return None

    def add_news_items(self, news_items) -> bool:
        try:
            response = requests.post(f"{self.api_url}/worker/news-items", json=news_items, headers=self.headers, verify=self.verify)

            return response.ok
        except Exception:
            logger.log_debug_trace("Cannot add Newsitem")
            return False

    def cleanup_token_blacklist(self):
        try:
            url = f"{self.api_url}/worker/token-blacklist"
            response = requests.post(url=url, headers=self.headers, verify=self.verify)
            return self.check_response(response, url)
        except Exception:
            logger.log_debug_trace("Cannot cleanup token blacklist")
            return False
