import base64
import datetime
import hashlib
from urllib.parse import urlparse, urljoin
import requests

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector


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

    def set_api_url(self):
        self.api_url = urljoin(self.base_url, self.api)

    def set_base_url(self, base_url):
        if not base_url:
            logger.warning("No BASE_URL set")
            raise ValueError("No BASE_URL set")
        parsed = urlparse(base_url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Invalid BASE_URL, must be http or https")
        self.base_url = base_url

    def set_headers(self, rt_token):
        if not rt_token:
            logger.warning("No RT_TOKEN set")
            raise ValueError("No RT_TOKEN set")
        self.headers = {"Authorization": f"token {rt_token}"}

    def setup_collector(self, source):
        if err := self.set_base_url(source.get("parameters").get("BASE_URL", None)):
            raise ValueError(err)
        self.set_api_url()

        logger.info(f"Website {source.get('id')} Starting collector for url: {self.base_url}")

        if err := self.set_headers(source.get("parameters").get("RT_TOKEN", None)):
            raise ValueError(err)

    def preview_collector(self, source):
        if err := self.setup_collector(source):
            raise ValueError(err)

        if tickets := self.rt_collector(source):
            return self.preview(tickets, source)

    def collect(self, source):
        if err := self.setup_collector(source):
            raise ValueError(err)

        try:
            if tickets := self.rt_collector(source):
                return self.publish(tickets, source)
        except Exception as e:
            logger.exception()
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            raise RuntimeError("RT Collector not available") from e

    def get_ids_from_tickets(self, tickets) -> list:
        return [ticket.get("id") for ticket in tickets.get("items", [])]

    def get_ticket_transaction(self, ticket_id: int) -> int:
        response = requests.get(f"{self.api_url}ticket/{ticket_id}/history", headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Ticket transaction for {ticket_id} returned with {response.status_code}")
            raise ValueError("No ticket history returned")
        return response.json().get("items")[0].get("_url").rsplit("/", 1)[1]

    def check_attach_for_text(self, attachment_items) -> list:
        attachment_ids = [attachment.get("_url").rsplit("/", 1)[1] for attachment in attachment_items]
        valid_text_attachments = []
        for id in attachment_ids:
            attachment = requests.get(f"{self.api_url}attachment/{id}", headers=self.headers)
            if not attachment or not attachment.ok:
                logger.error(f"Attachment of id: {id} returned with {attachment.status_code}")
                raise ValueError("No attachment returned")
            content_type = attachment.json().get("ContentType", "")
            if content_type.startswith("multipart") or content_type.startswith("text"):
                valid_text_attachments.append(id)

        return valid_text_attachments

    def get_content_attachment_data(self, transaction: int) -> tuple[list, str, str]:
        ticket_transaction = requests.get(f"{self.api_url}transaction/{transaction}", headers=self.headers)
        if not ticket_transaction or not ticket_transaction.ok:
            logger.error(f"Ticket transaction returned with {ticket_transaction.status_code}")
            raise ValueError("No transaction returned")
        # Limiting to only two relevant attachments.
        if len(ticket_transaction.json().get("_hyperlinks")) > 2:
            attachment_items = [
                item for item in ticket_transaction.json().get("_hyperlinks")[:3] if item.get("ref", "").startswith("attachment")
            ]
        else:
            attachment_items = [item for item in ticket_transaction.json().get("_hyperlinks") if item.get("ref", "").startswith("attachment")]

        return (
            self.check_attach_for_text(attachment_items),
            ticket_transaction.json().get("Created"),
            ticket_transaction.json().get("Creator").get("id"),
        )

    def decode64(self, ticket_content) -> str:
        if isinstance(ticket_content, str):
            ticket_content = base64.b64decode(ticket_content).decode("utf-8")
            return ticket_content
        logger.error("Unable to decode the ticket content")
        raise ValueError("ticket_content is not a string")

    def get_ticket_subject(self, attachment) -> str:
        return attachment.get("Subject")

    def get_ticket_content(self, attachment) -> str:
        ticket_content = attachment.get("Content")
        return self.decode64(ticket_content)

    def get_ticket_data(self, ticket_id: int, source) -> dict:
        ticket_transaction = self.get_ticket_transaction(ticket_id)
        ticket_attachment_id, ticket_published, ticket_author = self.get_content_attachment_data(ticket_transaction)

        attachment = requests.get(f"{self.api_url}attachment/{ticket_attachment_id[0]}", headers=self.headers)
        if not attachment or not attachment.ok:
            logger.error(f"Ticket of id: {ticket_id} returned with {attachment.status_code}")
            raise ValueError("No ticket attachment returned")
        ticket_subject = self.get_ticket_subject(attachment.json())

        # Tickets don't form uniform transactions.
        # This covers a case, where in the first attachment is the subject, and in the second attach is the content.
        if len(ticket_attachment_id) > 1:
            attachment = requests.get(f"{self.api_url}attachment/{ticket_attachment_id[1]}", headers=self.headers)
            if not attachment or not attachment.ok:
                logger.error(f"Ticket of id: {ticket_id} returned with {attachment.status_code}")
                raise ValueError("No ticket attachment returned")

        ticket_content = self.get_ticket_content(attachment.json())
        for_hash: str = str(ticket_id) + ticket_content

        return {
            "id": str(ticket_id),
            "hash": hashlib.sha256(for_hash.encode()).hexdigest(),
            "title": ticket_subject,
            "review": "",
            "source": self.base_url,
            "link": f"{self.base_url}{self.ticket_path}{ticket_id}",
            "published": datetime.datetime.fromisoformat(ticket_published),
            "author": ticket_author,
            "collected": datetime.datetime.now(),
            "content": ticket_content,
            "osint_source_id": source.get("id"),
            "attributes": [],
        }

    def get_tickets(self, ticket_ids: list, source) -> list:
        return [self.get_ticket_data(ticket_id, source) for ticket_id in ticket_ids]

    def rt_collector(self, source):
        response = requests.get(f"{self.api_url}tickets?query=*", headers=self.headers)
        if not response or not response.ok:
            logger.error(f"Website {source.get('id')} returned no content with response: {response}")
            raise ValueError("Website returned no content, check your RT_TOKEN")

        if not (tickets_ids_list := self.get_ids_from_tickets(response.json())):
            logger.error(f"No tickets found for {self.base_url}")
            raise ValueError("No tickets available")

        try:
            tickets = self.get_tickets(tickets_ids_list, source)
        except RuntimeError as e:
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            raise RuntimeError(f"RT Collector for {self.base_url} failed with error: {str(e)}") from e

        return tickets
