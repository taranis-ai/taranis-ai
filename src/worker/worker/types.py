from requests import Response
from datetime import datetime
import langcodes


class Product:
    def __init__(self, response: Response):
        self.data: bytes = response.content
        self.mime_type: str = response.headers["Content-Type"]


class NewsItem:
    def __init__(
        self,
        osint_source_id: str,
        hash: str = "",
        author: str = "",
        title: str = "",
        language: str | None = None,
        review: str | None = None,
        content: str = "",
        web_url: str = "",
        source: str = "",
        published_date: datetime | None = None,
        collected_date: datetime = datetime.now(),
        attributes: list | None = None,
    ):
        self.osint_source_id = osint_source_id
        self.hash = hash
        self.author = author
        self.title = title
        self.language = self.normalize_language_code(language) if language else None
        self.review = review
        self.content = content
        self.web_url = web_url
        self.source = source
        if not published_date:
            published_date = collected_date
        self.published_date = published_date
        self.collected_date = collected_date
        self.attributes = attributes or []

    def to_dict(self):
        data = {
            "hash": self.hash,
            "title": self.title,
            "source": self.source,
            "link": self.web_url,
            "published": self.published_date.isoformat(),
            "author": self.author,
            "collected": self.collected_date.isoformat(),
            "content": self.content,
            "osint_source_id": self.osint_source_id,
            "attributes": self.attributes,
        }
        if self.language:
            data["language"] = self.language
        if self.review:
            data["review"] = self.review
        return data

    def normalize_language_code(self, input_code: str) -> str | None:
        try:
            lang = langcodes.find(input_code)
            return lang.language
        except LookupError:
            return None
