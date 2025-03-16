import base64
import hashlib
from urllib.parse import urlparse, urljoin
import requests
from datetime import datetime

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector, NoChangeError
from worker.types import NewsItem


class RTCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "RT_COLLECTOR"
        self.name = "RT Collector"
        self.description = "Collector for gathering data from Request Tracker"
        self.base_url = ""
        self.api_url = ""
        self.api = "/REST/2.0/"
        self.ticket_path = "/Ticket/Display.html?id="
        self.search_query = "*"
        self.fields_to_include = ""
        self.timeout = 60
        self.last_attempted = None

    def set_api_url(self):
        self.api_url = urljoin(self.base_url, self.api)

    def set_base_url(self, base_url):
        if not base_url:
            raise ValueError("No BASE_URL set")
        parsed = urlparse(base_url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Invalid BASE_URL, must be http or https")
        self.base_url = base_url

    def set_auth_header(self, rt_token):
        if not rt_token:
            raise ValueError("No RT_TOKEN set")
        self.headers = {"Authorization": f"token {rt_token}"}

    def parse_fields_to_include(self, fields_to_include):
        self.fields_to_include = [field.strip() for field in fields_to_include.split(",")]

    def setup_collector(self, source):
        logger.info(f"Website {source.get('id')} Starting collector for url: {self.base_url}")
        self.set_auth_header(source.get("parameters").get("RT_TOKEN", None))
        super().parse_source(source)
        self.set_base_url(source.get("parameters").get("BASE_URL", None))
        self.set_api_url()

        if search_query := source.get("parameters").get("SEARCH_QUERY", None):
            self.search_query = search_query
        if fields_to_include := source.get("parameters").get("FIELDS_TO_INCLUDE", None):
            self.parse_fields_to_include(fields_to_include)

    def preview_collector(self, source: dict) -> list[dict]:
        self.setup_collector(source)

        if story_list := self.rt_collector(source):
            return self.preview([item for story in story_list for item in story.get("news_items", [])], source)

        return []

    def collect(self, source: dict, manual: bool = False):
        self.setup_collector(source)

        try:
            if story_dicts := self.rt_collector(source):
                return self.publish_or_update_stories(story_dicts, source, "rt_id")
        except Exception as e:
            raise RuntimeError(f"RT Collector not available {self.base_url} with exception: {e}") from e

    @staticmethod
    def to_story_dict(title: str, news_items_list: list[NewsItem], attributes: list[dict]) -> dict:
        return {
            "title": title,
            "attributes": attributes,
            "news_items": news_items_list,
        }

    def decode64(self, ticket_content) -> str:
        if isinstance(ticket_content, str):
            ticket_content = base64.b64decode(ticket_content).decode("utf-8")
            return ticket_content
        logger.error("Unable to decode the ticket content")
        raise ValueError("ticket_content is not a string")

    def get_unique_content_from_hyperlinks(self, hyperlinks_full) -> list[dict]:
        """Clean up `_hyperlinks` from `CustomFields`"""
        return [hyperlink for hyperlink in hyperlinks_full if hyperlink.get("type") != "customfield"]

    def extract_ticket_attributes(
        self,
        ticket: dict,
        ticket_custom_fields: list[dict],
        hyperlinks_unique: list[dict],
        ticket_id: int,
        published_date: str,
    ) -> list[dict]:
        """
        Build the final list of attributes from:
            1. Top-level ticket fields (strings, numbers, booleans only),
            2. CustomFields,
            3. hyperlink data (already processed).
        """
        top_level_attributes: list[dict] = []
        top_level_attributes.extend({"name": key, "values": [value]} for key, value in ticket.items() if not isinstance(value, (dict, list)))

        ticket_fields = top_level_attributes + ticket_custom_fields + hyperlinks_unique

        attributes = [
            {"key": attr.get("name", ""), "value": attr.get("values", [None])[0]}
            for attr in ticket_fields
            if attr.get("values") and (not self.fields_to_include or (attr.get("name", "") in self.fields_to_include))
        ]

        if not attributes:
            attributes = [{"key": "rt_id", "value": f"{ticket_id}/{published_date}"}]
        else:
            attributes.append({"key": "rt_id", "value": f"{ticket_id}/{published_date}"})

        return attributes

    def news_items_to_story(self, ticket_id: int, news_items: list) -> dict:
        ticket = self.get_ticket(ticket_id)

        ticket_custom_fields: list[dict] = ticket.pop("CustomFields", [])
        ticket_hyperlinks: list[dict] = ticket.pop("_hyperlinks", [])
        title: str = ticket.get("Subject", "No title found")
        published_date: str = ticket.get("Created", "")
        hyperlinks_unique: list[dict] = self.get_unique_content_from_hyperlinks(ticket_hyperlinks)
        attributes = self.extract_ticket_attributes(ticket, ticket_custom_fields, hyperlinks_unique, ticket_id, published_date)

        return self.to_story_dict(title, news_items, attributes)

    def get_attachment_news_item(self, ticket_id: int, attachment: dict, source: dict) -> NewsItem:
        content = attachment.get("Content", "")
        created = attachment.get("Created", "")
        author = attachment.get("Creator", {}).get("id", "")

        for_hash: str = str(ticket_id) + created + author + (content or "")
        decoded_content: str = self.decode64(content) if content else ""
        return NewsItem(
            osint_source_id=source.get("id", ""),
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            title="attachment",
            content=decoded_content or "attachment without content",
            published_date=datetime.fromisoformat(created),
            author=author,
            review=source.get("review", ""),
            source=self.base_url,
            web_url=self.base_url + self.ticket_path + str(ticket_id),
        )

    def get_attachment_values(self, attachment_url: str) -> dict:
        try:
            response = self.send_get_request(attachment_url, self.last_attempted)
            return response.json()
        except (NoChangeError, requests.exceptions.RequestException) as e:
            logger.error(f"Failed to get attachement value from {attachment_url}. Error: {e}")
            return {}

    def get_ticket_attachments(self, ticket_id: int) -> list:
        """An Attachment represents a NewsItem"""
        attachments_content: list[dict] = []

        attachments_url = urljoin(self.api_url, f"ticket/{ticket_id}/attachments")
        try:
            response = self.send_get_request(attachments_url, self.last_attempted)
            ticket_attachments: list[dict] = response.json().get("items", [])
            attachments_content.extend(self.get_attachment_values(attachment.get("_url", "")) for attachment in ticket_attachments)
        except (NoChangeError, requests.exceptions.RequestException) as e:
            logger.error(f"Failed to get ticket attachements from {attachments_url}. Error: {e}")
            return []
        return attachments_content or []

    def get_ticket(self, ticket_id: int) -> dict:
        ticket_url = urljoin(self.api_url, f"ticket/{ticket_id}")
        try:
            response = self.send_get_request(ticket_url, self.last_attempted)
            return response.json()
        except (NoChangeError, requests.exceptions.RequestException) as e:
            logger.error(f"Failed to get ticket from {ticket_url}. Error: {e}")
            return {}

    def get_story_dict(self, ticket_id: int, source) -> dict:
        story_news_items = []
        if ticket_attachments := self.get_ticket_attachments(ticket_id):
            story_news_items.extend(self.get_attachment_news_item(ticket_id, attachment, source) for attachment in ticket_attachments)
        return self.news_items_to_story(ticket_id, story_news_items)

    def get_stories(self, ticket_ids: list, source) -> list[dict]:
        """A Ticket represents a Story"""
        return [self.get_story_dict(ticket_id, source) for ticket_id in ticket_ids]

    def update_rt_favicon(self, osint_source_id):
        icon_url = f"{urlparse(self.base_url).scheme}://{urlparse(self.base_url).netloc}/static/images/favicon.png"
        r = requests.get(icon_url, headers=self.headers, proxies=self.proxies)
        if not r.ok:
            return None

        icon_content = {"file": (r.headers.get("content-disposition", "file"), r.content)}
        self.core_api.update_osint_source_icon(osint_source_id, icon_content)
        return None

    def rt_collector(self, source) -> list[dict]:
        self.last_attempted = self.get_last_attempted(source)

        logger.info(f"Searching for tickets with query: {self.search_query}")
        response = self.send_get_request(f"{self.api_url}tickets?query={self.search_query}", self.last_attempted)

        try:
            tickets_ids_list = [ticket.get("id") for ticket in response.json().get("items", [])]
        except requests.exceptions.JSONDecodeError:
            raise RuntimeError("Could not decode result of query as JSON")

        if not tickets_ids_list:
            raise RuntimeError(f"No tickets available for {self.api_url}")

        if not self.last_attempted:
            self.update_rt_favicon(self.osint_source_id)

        try:
            story_dicts: list[dict] = self.get_stories(tickets_ids_list, source)
        except RuntimeError as e:
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            raise RuntimeError(f"RT Collector for {self.base_url} failed with error: {str(e)}") from e

        return story_dicts
