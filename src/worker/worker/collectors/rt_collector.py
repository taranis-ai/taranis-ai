import base64
import datetime
import hashlib
from urllib.parse import urlparse, urljoin
import requests
import json

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector
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

    def set_api_url(self):
        self.api_url = urljoin(self.base_url, self.api)

    def set_base_url(self, base_url):
        if not base_url:
            raise ValueError("No BASE_URL set")
        parsed = urlparse(base_url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Invalid BASE_URL, must be http or https")
        self.base_url = base_url

    def set_headers(self, rt_token):
        if not rt_token:
            raise ValueError("No RT_TOKEN set")
        self.headers = {"Authorization": f"token {rt_token}"}

    def setup_collector(self, source):
        self.set_base_url(source.get("parameters").get("BASE_URL", None))
        self.set_api_url()

        logger.info(f"Website {source.get('id')} Starting collector for url: {self.base_url}")

        self.set_headers(source.get("parameters").get("RT_TOKEN", None))

        if search_query := source.get("parameters").get("SEARCH_QUERY", None):
            self.search_query = search_query
        if additional_headers := source["parameters"].get("ADDITIONAL_HEADERS", None):
            self.update_headers(additional_headers)

    def preview_collector(self, source: dict) -> list[dict]:
        self.setup_collector(source)

        if story_list := self.rt_collector(source):
            return self.preview([item for news_item_list in story_list for item in news_item_list], source)

        return []

    def collect(self, source: dict, manual: bool = False):
        self.setup_collector(source)

        try:
            if tickets := self.rt_collector(source):
                story_dicts = [RTCollector.to_story_dict(news_items_list) for news_items_list in tickets]
                return self.publish_stories(story_dicts, source)
        except Exception as e:
            raise RuntimeError(f"RT Collector not available {self.base_url} with exception: {e}") from e

    @staticmethod
    def to_story_dict(news_items_list: list[NewsItem]) -> dict:
        # Get title and attributes from the first news item (meta item)
        story_title = news_items_list[0].title
        story_attributes = news_items_list[0].attributes
        return {
            "title": story_title,
            "attributes": story_attributes,
            "news_items": news_items_list,
        }

    def get_ids_from_tickets(self, tickets) -> list:
        return [ticket.get("id") for ticket in tickets.get("items", [])]

    def decode64(self, ticket_content) -> str:
        if isinstance(ticket_content, str):
            ticket_content = base64.b64decode(ticket_content).decode("utf-8")
            return ticket_content
        logger.error("Unable to decode the ticket content")
        raise ValueError("ticket_content is not a string")

    def get_unique_content_from_hyperlinks(self, hyperlinks_full) -> list[dict]:
        """Clean up `_hyperlinks` from `CustomFields`"""
        return [hyperlink for hyperlink in hyperlinks_full if hyperlink.get("type") != "customfield"]

    def get_meta_news_item(self, ticket_id: int, source: dict) -> NewsItem:
        ticket = self.get_ticket(ticket_id)

        ticket_custom_fields: list[dict] = ticket.pop("CustomFields")
        ticket_hyperlinks: list = ticket.pop("_hyperlinks")
        title: str = ticket.get("Subject", "No title found")
        metadata: str = self.json_to_string(ticket)

        hyperlinks_unique: list[dict] = self.get_unique_content_from_hyperlinks(ticket_hyperlinks)
        ticket_fields: list[dict] = ticket_custom_fields + hyperlinks_unique
        for_hash: str = str(ticket_id) + ticket.get("Subject", "") + ticket.get("Created", "")  # TODO: check what the ideal hash should be
        attributes = [
            {"key": attr.get("name", ""), "value": attr.get("values", [])[0]} for attr in ticket_custom_fields if attr.get("values")
        ] or []
        print(f"{attributes=}")

        return NewsItem(
            osint_source_id=source.get("id", ""),
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            title=title,
            content=str(ticket_id) + str(ticket_fields) + metadata,
            web_url=f"{self.base_url}{self.ticket_path}{ticket_id}",
            published_date=datetime.datetime.fromisoformat(ticket.get("Created", "")),
            author=ticket.get("Owner", {}).get("id", ""),
            collected_date=datetime.datetime.now(),
            language=source.get("language", ""),
            review=source.get("review", "metadata"),
            attributes=attributes,
        )

    def get_attachment_news_item(self, ticket_id: int, attachment: dict, source: dict) -> NewsItem:
        for_hash: str = str(ticket_id) + attachment.get("Content", "")

        return NewsItem(
            osint_source_id=source.get("id", ""),
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            title="attachment",
            content=self.decode64(attachment.get("Content", "")),
            web_url=f"{self.base_url}{self.ticket_path}{ticket_id}",
            published_date=datetime.datetime.fromisoformat(attachment.get("Created", "")),
            author=attachment.get("Creator", {}).get("id", ""),
            collected_date=datetime.datetime.now(),
            language=source.get("language", ""),
            review=source.get("review", ""),
            attributes=[],
        )

    def get_attachment_values(self, attachment_url: str) -> dict:
        response = requests.get(attachment_url, headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Attachment of url: {attachment_url} returned with {response.status_code}")
            raise ValueError("No attachment content returned")
        return response.json()

    def get_ticket_attachments(self, ticket_id: int, source: dict) -> list:
        """An Attachment represents a NewsItem"""
        if response := requests.get(
            f"{self.api_url}ticket/{ticket_id}/attachments",
            headers=self.headers,
        ):
            ticket_attachments: list[dict] = response.json().get("items", [])
            attachments_content: list[dict] = []
            attachments_content.extend(self.get_attachment_values(attachment.get("_url", "")) for attachment in ticket_attachments)
        return attachments_content or []

    def json_to_string(self, json_data) -> str:
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        result = [f"{key}: {json.dumps(value)}" for key, value in json_data.items()]
        return "\n".join(result)

    def get_ticket(self, ticket_id: int) -> dict:
        response = requests.get(f"{self.api_url}ticket/{ticket_id}", headers=self.headers)
        return response.json()

    def get_story_news_items(self, ticket_id: int, source) -> list[NewsItem]:
        story_news_items = [self.get_meta_news_item(ticket_id, source)]
        if ticket_attachments := self.get_ticket_attachments(ticket_id, source):
            for attachment in ticket_attachments:
                if attachment.get("Content", ""):
                    story_news_items.append(self.get_attachment_news_item(ticket_id, attachment, source))

        return story_news_items

    def get_news_item_lists(self, ticket_ids: list, source) -> list[list[NewsItem]]:
        """A Ticket represents a Story"""
        return [self.get_story_news_items(ticket_id, source) for ticket_id in ticket_ids]

    def rt_collector(self, source) -> list[list[NewsItem]]:
        response = requests.get(f"{self.api_url}tickets?query={self.search_query}", headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Website {source.get('id')} returned no content with response: {response}")
            raise ValueError("Website returned no content, check your RT_TOKEN")

        if not (tickets_ids_list := self.get_ids_from_tickets(response.json())):
            logger.error(f"No tickets found for {self.base_url}")
            raise ValueError("No tickets available")

        try:
            tickets: list[list[NewsItem]] = self.get_news_item_lists(tickets_ids_list, source)
        except RuntimeError as e:
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            raise RuntimeError(f"RT Collector for {self.base_url} failed with error: {str(e)}") from e

        return tickets


if __name__ == "__main__":
    rt_collector = RTCollector()
    rt_collector.collect(
        {
            "description": "",
            "id": "752cae6a-9d48-463e-a91e-1365f6d96eb4",
            "last_attempted": None,
            "last_collected": None,
            "last_error_message": None,
            "name": "rt collector",
            "parameters": {
                "BASE_URL": "http://rt.lab",
                "RT_TOKEN": "1-14-f56697548241b7c1fbc51522b34e8efb",
                # "SEARCH_QUERY": "Started > '2018-04-04' AND Status != 'resolved'",
            },
            "state": -1,
            "type": "rt_collector",
            "word_lists": [],
        }
    )
