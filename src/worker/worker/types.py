from requests import Response
from datetime import datetime


class Product:
    def __init__(self, response: Response):
        self.data: bytes = response.content
        self.mime_type: str = response.headers["Content-Type"]


class NewsItem:
    def __init__(
        self,
        source_id: str,
        hash: str = "",
        author: str = "",
        title: str = "",
        content: str = "",
        web_url: str = "",
        published_date: datetime | None = None,
        collected_date: datetime = datetime.now(),
        attributes: list = None,
    ):
        self.source_id = source_id
        self.hash = hash
        self.author = author
        self.title = title
        self.content = content
        self.web_url = web_url
        if not published_date:
            published_date = collected_date
        self.published_date = published_date
        self.collected_date = collected_date
        self.attributes = attributes or []

    def to_dict(self):
        return {
            "hash": self.hash,
            "title": self.title,
            "source": self.web_url,
            "link": self.web_url,
            "published": self.published_date,
            "author": self.author,
            "collected": self.collected_date,
            "content": self.content,
            "osint_source_id": self.source_id,
            "attributes": self.attributes,
        }
