import datetime

from models.assess import NewsItem

from .base_web_collector import BaseWebCollector


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
        self.parse_source(source)
        self.twitter_collector(source, manual)

    def twitter_collector(self, source: dict, manual: bool = False):
        news_items = []

        response = self.send_get_request(self.web_url, self.last_attempted)

        response.raise_for_status()
        public_tweets = response.json()["data"]

        for tweet in public_tweets:
            link = f"https://twitter.com/{tweet.username}/status/{tweet.id}"
            author = tweet.username
            published = tweet.created_at
            title = f"Twitter post from @{author}"
            content = tweet.text

            news_item = NewsItem(
                osint_source_id=str(source["id"]),
                title=title,
                link=link,
                published=published,
                author=author,
                content=content,
                language=source.get("language", ""),
                attributes=[],
            )

            news_items.append(news_item)

        self.publish(news_items, source)
