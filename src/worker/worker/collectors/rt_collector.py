import base64
import datetime
import hashlib
from typing import Sequence
from urllib.parse import urlparse, urljoin
import requests
import json
import rt.rest2

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
        self.rt = None

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
        self.rt = rt.rest2.Rt(self.base_url + self.api, token=rt_token)

    def setup_collector(self, source):
        self.set_base_url(source.get("parameters").get("BASE_URL", None))
        self.set_api_url()

        logger.info(f"Website {source.get('id')} Starting collector for url: {self.base_url}")

        self.set_headers(source.get("parameters").get("RT_TOKEN", None))

        if additional_headers := source["parameters"].get("ADDITIONAL_HEADERS", None):
            self.update_headers(additional_headers)

    def preview_collector(self, source: dict) -> list[dict]:
        self.setup_collector(source)

        if tickets := self.rt_collector(source):
            return self.preview(tickets, source)

        return []

    def collect(self, source: dict, manual: bool = False):
        self.setup_collector(source)

        try:
            if tickets := self.rt_collector(source):
                return self.publish(tickets, source)
        except Exception as e:
            raise RuntimeError(f"RT Collector not available {self.base_url} with exception: {e}") from e

    def get_ids_from_tickets(self, tickets) -> list:
        return [ticket.get("id") for ticket in tickets.get("items", [])]

    def decode64(self, ticket_content) -> str:
        if isinstance(ticket_content, str):
            ticket_content = base64.b64decode(ticket_content).decode("utf-8")
            logger.debug(f"{ticket_content=}")
            return ticket_content
        logger.error("Unable to decode the ticket content")
        raise ValueError("ticket_content is not a string")

    def get_ticket_subject(self, attachment) -> str:
        return attachment.get("Subject")

    def get_ticket_content(self, attachment) -> str:
        ticket_content = attachment.get("Content")
        return self.decode64(ticket_content)

    def get_unique_content_from_hyperlinks(self, hyperlinks_full) -> list[dict]:
        """Clean up `_hyperlinks` from `CustomFields`"""
        return [hyperlink for hyperlink in hyperlinks_full if hyperlink.get("type") != "customfield"]

    def get_meta_news_item(self, ticket_id: int, source: dict) -> NewsItem:
        ticket = self.get_ticket(ticket_id)

        ticket_custom_fields: list[dict] = ticket.pop("CustomFields")
        ticket_hyperlinks: list = ticket.pop("_hyperlinks")
        title: str = ticket.get("Subject", "No title found")
        metadata: str = self.json_to_string(ticket)
        logger.debug(f"{title=}")
        logger.debug(f"{metadata=}")
        logger.debug(f"{ticket_custom_fields=}")

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

    def get_attachment_news_item(self, ticket_id: int, attachments: dict, source: dict) -> NewsItem:
        attachment = self.get_attachment(attachments.get("_url", ""))
        logger.debug(f"{attachment=}")

        for_hash: str = str(ticket_id) + attachment.get("Content", "")

        return NewsItem(
            osint_source_id=source.get("id", ""),
            hash=hashlib.sha256(for_hash.encode()).hexdigest(),
            title="attachment",
            content=self.decode64(attachment.get("Content", "")),
            web_url=f"{self.base_url}{self.ticket_path}{ticket_id}",
            published_date=datetime.datetime.fromisoformat(attachment.get("Created", "")),
            author=attachments.get("Creator", {}).get("id", ""),
            collected_date=datetime.datetime.now(),
            language=source.get("language", ""),
            review=source.get("review", ""),
            attributes=[],
        )

    def get_attachment(self, attachment_url: str) -> dict:
        response = requests.get(attachment_url, headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Attachment of url: {attachment_url} returned with {response.status_code}")
            raise ValueError("No attachment content returned")
        return response.json()

    def get_news_items(self, ticket_id: int, source: dict) -> list[NewsItem]:
        if self.rt:
            ticket_attachments: Sequence[dict[str, str]] = self.rt.get_attachments(ticket_id)
            logger.debug(f"{ticket_attachments=}")
            return [self.get_attachment_news_item(ticket_id, attachment, source) for attachment in ticket_attachments]
        return []

    def json_to_string(self, json_data) -> str:
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        result = [f"{key}: {json.dumps(value)}" for key, value in json_data.items()]
        return "\n".join(result)

    def get_ticket(self, ticket_id: int) -> dict:
        response = requests.get(f"{self.api_url}ticket/{ticket_id}", headers=self.headers)
        return response.json()

    def get_tickets(self, ticket_ids: list, source) -> list[NewsItem]:
        ticket_news_items = []
        for ticket_id in ticket_ids:
            ticket_news_items.append(self.get_meta_news_item(ticket_id, source))
            if news_items := self.get_news_items(ticket_id, source):
                ticket_news_items.extend(news_items)

        return ticket_news_items

    def rt_collector(self, source) -> list[NewsItem]:
        response = requests.get(f"{self.api_url}tickets?query=*", headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Website {source.get('id')} returned no content with response: {response}")
            raise ValueError("Website returned no content, check your RT_TOKEN")

        if not (tickets_ids_list := self.get_ids_from_tickets(response.json())):
            logger.error(f"No tickets found for {self.base_url}")
            raise ValueError("No tickets available")

        try:
            tickets: list[NewsItem] = self.get_tickets(tickets_ids_list, source)
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
            "parameters": {"BASE_URL": "http://rt.lab", "RT_TOKEN": "1-14-f56697548241b7c1fbc51522b34e8efb"},
            "state": -1,
            "type": "rt_collector",
            "word_lists": [],
        }
    )
