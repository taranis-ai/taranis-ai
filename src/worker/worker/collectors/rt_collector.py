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

    def set_base_url(self, base_url) -> str | None:
        if not base_url:
            logger.warning("No BASE_URL set")
            return "No BASE_URL set"
        parsed = urlparse(base_url)
        if parsed.scheme not in ["http", "https"]:
            return "Invalid BASE_URL, must be http or https"
        self.base_url = base_url

    def set_headers(self, rt_token) -> str | None:
        if not rt_token:
            logger.warning("No RT_TOKEN set")
            return "No RT_TOKEN set"
        self.headers = {"Authorization": f"token {rt_token}"}

    def collect(self, source):
        if err := self.set_base_url(source["parameters"].get("BASE_URL", None)):
            return err
        self.set_api_url()

        logger.info(f"Website {source['id']} Starting collector for url: {self.base_url}")

        if err := self.set_headers(source["parameters"].get("RT_TOKEN", None)):
            return err

        try:
            return self.rt_collector(source)
        except Exception as e:
            logger.exception()
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            return "RT Collector not available"

    def get_ids_from_tickets(self, tickets) -> list:
        return [ticket["id"] for ticket in tickets.get("items", [])]

    def get_ticket_transaction(self, ticket_id: int) -> int:
        response = requests.get(f"{self.api_url}ticket/{ticket_id}/history", headers=self.headers)
        if not response or not response.ok:
            logger.info(f"Ticket transaction for {ticket_id} returned with {response.status_code}")
            raise ValueError("No ticket history returned")
        return response.json().get("items")[0].get("_url").rsplit("/", 1)[1]

    def check_attach_for_text(self, attachment_items) -> list:
        attachment_ids = [attachment.get("_url").rsplit("/", 1)[1] for attachment in attachment_items]
        for id in attachment_ids:
            attachment = requests.get(f"{self.api_url}attachment/{id}", headers=self.headers)
            if not attachment or not attachment.ok:
                logger.info(f"Attachment of id: {id} returned with {attachment.status_code}")
                raise ValueError("No attachment returned")
            content_type = attachment.json().get("ContentType", "")
            if content_type.startswith("multipart") or content_type.startswith("text"):
                continue
            else:
                attachment_ids.remove(id)

        return attachment_ids

    def get_content_attachment_data(self, transaction: int) -> tuple[list, str, str]:
        ticket_transaction = requests.get(f"{self.api_url}transaction/{transaction}", headers=self.headers)
        if not ticket_transaction or not ticket_transaction.ok:
            logger.info(f"Ticket transaction returned with {ticket_transaction.status_code}")
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
        return "ticket_content is not a string"

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
            logger.info(f"Ticket of id: {ticket_id} returned with {attachment.status_code}")
            raise ValueError("No ticket attachment returned")
        ticket_subject = self.get_ticket_subject(attachment.json())

        # Tickets don't form uniform transactions.
        # This covers a case, where in the first attachment is the subject, and in the second attach is the content.
        if len(ticket_attachment_id) > 1:
            attachment = requests.get(f"{self.api_url}attachment/{ticket_attachment_id[1]}", headers=self.headers)
            if not attachment or not attachment.ok:
                logger.info(f"Ticket of id: {ticket_id} returned with {attachment.status_code}")
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
            logger.info(f"Website {source.get('id')} returned no content with response: {response}")
            raise ValueError("Website returned no content, check your RT_TOKEN")

        if not (tickets_ids_list := self.get_ids_from_tickets(response.json())):
            raise ValueError("No tickets available")
        try:
            tickets = self.get_tickets(tickets_ids_list, source)
        except ValueError as e:
            logger.error(f"RT Collector for {self.base_url} failed with error: {str(e)}")
            return str(e)

        self.publish(tickets, source)
        return None


if __name__ == "__main__":
    rt_collector = RTCollector()
    rt_collector.collect({"id": 1, "parameters": {"BASE_URL": "http://localhost:8080",
                                                  "RT_TOKEN": "1-14-eb1314501df7b5e1c38359fd70ce149f"}})