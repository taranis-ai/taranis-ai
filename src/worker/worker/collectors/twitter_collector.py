import datetime
import hashlib

from .base_web_collector import BaseWebCollector
from worker.types import NewsItem


class TwitterCollector(BaseWebCollector):
    def __init__(self):
        super().__init__()
        self.type: str = "TWITTER_COLLECTOR"
        self.name: str = "Twitter Collector"
        self.description: str = "Collector for gathering data from Twitter"

        self.news_items: list[NewsItem] = []
        self.last_attempted: datetime.datetime | None = None
        self.search_keyword: str = ""
        self.web_url: str = "https://api.twitter.com/2/tweets/search/recent"

    def parse_source(self, source: dict):
        super().parse_source(source)
        self.search_keyword = source["parameters"].get("SEARCH_KEYWORD", "")

    def collect(self, source: dict, manual: bool = False):
        try:
            self.parse_source(source)
            return self.twitter_collector(source, manual)
        except Exception as e:
            raise RuntimeError(f"Twitter Collector failed with error: {e}") from e

    def twitter_collector(self, source: dict, manual: bool = False):
        news_items = []

        response = self.send_get_request(self.web_url, self.last_attempted)

        response.raise_for_status()
        public_tweets = response.json()["data"]

        for tweet in public_tweets:
            tweet_id = tweet.id
            link = f"https://twitter.com/{tweet.username}/status/{tweet.id}"
            author = tweet.username
            published = tweet.created_at
            title = f"Twitter post from @{author}"
            content = tweet.text

            for_hash = author + tweet_id + str(content)

            news_item = NewsItem(
                osint_source_id=source["id"],
                hash=hashlib.sha256(for_hash.encode()).hexdigest(),
                title=title,
                web_url=link,
                published_date=published,
                author=author,
                collected_date=datetime.datetime.now(),
                content=content,
                language=source.get("language", ""),
                attributes=[],
            )

            news_items.append(news_item)

        self.publish(news_items, source)
