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
        id: str | None = None,
        hash: str = "",
        author: str = "",
        title: str = "",
        language: str = "",
        review: str = "",
        content: str = "",
        web_url: str = "",
        source: str = "",
        published_date: datetime | None = None,
        collected_date: datetime | None = None,
        attributes: list | None = None,
        last_change: str = "external",
        story_id: str = "",
    ):
        self.osint_source_id = osint_source_id
        self.id = id
        self.hash = hash
        self.author = author
        self.title = title
        self.language = self.normalize_language_code(language) if language else ""
        self.review = review
        self.content = content
        self.web_url = web_url
        self.source = source
        if not collected_date:
            collected_date = datetime.now()
        self.collected_date = collected_date
        if not published_date:
            published_date = collected_date
        self.published_date = published_date
        self.attributes = attributes or []
        self.last_change = last_change
        self.story_id = story_id

    def to_dict(self):
        result = {
            "id": self.id,
            "hash": self.hash,
            "title": self.title,
            "source": self.source,
            "link": self.web_url,
            "published": self.published_date.isoformat(),
            "author": self.author,
            "collected": self.collected_date.isoformat(),
            "content": self.content,
            "osint_source_id": self.osint_source_id,
            "last_change": self.last_change,
            "story_id": self.story_id,
            "review": self.review,
            "language": self.language,
        }
        if self.attributes:
            result["attributes"] = self.attributes
        return result

    def normalize_language_code(self, input_code: str) -> str | None:
        try:
            lang = langcodes.find(input_code)
            return lang.language
        except LookupError:
            return None
