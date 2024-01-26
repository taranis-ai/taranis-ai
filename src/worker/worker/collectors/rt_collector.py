import base64
import datetime
import hashlib
import json
import requests
from html_sanitizer import Sanitizer

from worker.log import logger
from worker.collectors.base_web_collector import BaseWebCollector


class RTCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type = "RT_COLLECTOR"
        self.name = "RT Collector"
        self.description = "Collector for gathering data from Request Tracker"
        self.api = "/REST/2.0/"

    def collect(self, source):
        base_url = source["parameters"].get("BASE_URL", None)
        if not base_url:
            logger.warning("No BASE_URL set")
            return "No BASE_URL set"
        if not base_url.startswith("http"):
            return "Invalid BASE_URL, must be http or https"
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        logger.info(f"Website {source['id']} Starting collector for url: {base_url}")

        rt_token = source["parameters"].get("RT_TOKEN", None)
        if not rt_token:
            logger.warning("No RT_TOKEN set")
            return "No RT_TOKEN set"
        self.headers = {"Authorization": f"token {rt_token}"}

        try:
            return self.rt_collector(base_url, source)
        except Exception as e:
            logger.exception()
            logger.error(f"RT Collector for {base_url} failed with error: {str(e)}")
            return str(e)

    def get_ids_from_tickets(self, tickets) -> list:
        return [ticket["id"] for ticket in tickets.get("items", [])]

    # def get_ticket_transaction(id: int) -> int:
    #     t = s.get(f'{api_url}ticket/{id}/history', headers=headers).json()
    #
    #     return t.get('items')[0].get('_url').rsplit('/', 1)[1]

    def get_ticket_transaction(self, ticket_id: int, url: str) -> int:
        response = requests.get(f"{url}ticket/{ticket_id}/history", headers=self.headers)
        if not response or not response.ok:
            logger.info(f"Ticket transaction for {ticket_id} returned with {response.status_code}")
            raise ValueError("No ticket history returned")
        return response.json().get("items")[0].get("_url").rsplit("/", 1)[1]

    def check_attach_for_text(self, attachment_items, url: str) -> list:
        attachment_ids = [attachment.get("_url").rsplit("/", 1)[1] for attachment in attachment_items]
        for id in attachment_ids:
            attachment = requests.get(f"{url}attachment/{id}", headers=self.headers)
            if not attachment or not attachment.ok:
                logger.info(f"Attachment of id: {id} returned with {attachment.status_code}")
                raise ValueError("No attachment returned")
            content_type = attachment.json().get("ContentType", "")
            if content_type.startswith("multipart") or content_type.startswith("text"):
                continue
            else:
                attachment_ids.remove(id)

        return attachment_ids

    def get_content_attachment_id(self, transaction: int, url: str) -> list:
        ticket_transaction = requests.get(f"{url}transaction/{transaction}", headers=self.headers)
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

        return self.check_attach_for_text(attachment_items, url)

    def sanitize(self, raw_ticket_string) -> str:
        # sanitizer = Sanitizer(
        #     {
        #         # tags: can't be left empty
        #         "tags": ("random", "tags"),
        #         "attributes": {},
        #         "empty": set(),
        #         "separate": set(),
        #     }
        # )
        #
        # if isinstance(raw_ticket_string, str):
        #     return sanitizer.sanitize(raw_ticket_string).strip()
        #
        # return "raw_ticket_string is not a string"
        return raw_ticket_string

    def decode64(self, ticket_content):
        if isinstance(ticket_content, str):
            ticket_content = base64.b64decode(ticket_content).decode("utf-8")
            return self.sanitize(ticket_content)
        return "ticket_content is not a string"

    def get_ticket_subject(self, attachment):
        ticket_subject = attachment.get("Subject")
        return self.sanitize(ticket_subject)

    def get_ticket_content(self, attachment):
        ticket_content = attachment.get("Content")
        return self.decode64(ticket_content)

    def get_ticket_data(self, ticket_id: int, url: str, source) -> dict:
        ticket_transaction = self.get_ticket_transaction(ticket_id, url)
        ticket_attachment_id = self.get_content_attachment_id(ticket_transaction, url)

        attachment = requests.get(f"{url}attachment/{ticket_attachment_id[0]}", headers=self.headers)
        if not attachment or not attachment.ok:
            logger.info(f"Ticket of id: {ticket_id} returned with {attachment.status_code}")
            raise ValueError("No ticket attachment returned")
        ticket_subject = self.get_ticket_subject(attachment.json())

        # Tickets don't form uniform transactions.
        # This covers a case, where in the first attachment is the subject, and in the second attach is the content.
        if len(ticket_attachment_id) > 1:
            attachment = requests.get(f"{url}attachment/{ticket_attachment_id[1]}", headers=self.headers)
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
            "source": "web_url",
            "link": "web_url",
            "published": datetime.datetime.now(),
            "author": "author",
            "collected": datetime.datetime.now(),
            "content": ticket_content,
            "osint_source_id": source["id"],
            "attributes": [],
        }

    def get_tickets(self, ticket_ids: list, url: str, source) -> list:
        return [self.get_ticket_data(ticket_id, url, source) for ticket_id in ticket_ids]

    def rt_collector(self, web_url: str, source):
        url = f"{web_url}{self.api}"
        tickets = None
        response = requests.get(f"{url}tickets?query=*", headers=self.headers)
        if not response or not response.ok:
            logger.info(f"Website {source['id']} returned no content")
            raise ValueError("Website returned no content, check your TOKEN")

        if tickets_ids_list := self.get_ids_from_tickets(response.json()):
            try:
                tickets = self.get_tickets(tickets_ids_list, url, source)
            except ValueError as e:
                logger.error(f"RT Collector for {web_url} failed with error: {str(e)}")
                return str(e)

        else:
            raise ValueError("No tickets available")
        self.publish(tickets, source)
        return None
