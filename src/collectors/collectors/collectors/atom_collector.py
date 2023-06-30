import datetime
import hashlib
import uuid
import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse

from collectors.managers.log_manager import logger
from .base_collector import BaseCollector
from shared.schema.news_item import NewsItemData


class AtomCollector(BaseCollector):
    type = "ATOM_COLLECTOR"
    name = "Atom Collector"
    description = "Collector for gathering data from Atom feeds"

    news_items = []

    def collect(self, source):
        feed_url = source["parameter_values"]["ATOM_FEED_URL"]
        user_agent = source["parameter_values"]["USER_AGENT"]
        interval = source["parameter_values"]["REFRESH_INTERVAL"]

        if not feed_url:
            return

        proxies = {}
        if "PROXY_SERVER" in source["parameter_values"]:
            proxy_server = source["parameter_values"]["PROXY_SERVER"]
            if proxy_server.startswith("https://"):
                proxies["https"] = proxy_server
            elif proxy_server.startswith("http://"):
                proxies["http"] = proxy_server
            else:
                proxies["http"] = f"http://{proxy_server}"

        try:
            if proxies:
                atom_xml = requests.get(feed_url, headers={"User-Agent": user_agent}, proxies=proxies)
                feed = feedparser.parse(atom_xml.text)
            else:
                feed = feedparser.parse(feed_url)

            news_items = []

            for feed_entry in feed["entries"]:
                limit = BaseCollector.history(interval)
                published = feed_entry["updated"]
                published = parse(published)

                if str(published) > str(limit):
                    link_for_article = feed_entry["link"]

                    if proxies:
                        page = requests.get(
                            link_for_article,
                            headers={"User-Agent": user_agent},
                            proxies=proxies,
                        )
                    else:
                        page = requests.get(link_for_article, headers={"User-Agent": user_agent})

                    if html_content := page.text:
                        content = BeautifulSoup(html_content, features="html.parser").text
                    else:
                        content = ""

                    description = feed_entry["summary"][:500].replace("<p>", " ")

                    for_hash = feed_entry["author"] + feed_entry["title"] + feed_entry["link"]

                    news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        feed_entry["title"],
                        description,
                        feed_url,
                        feed_entry["link"],
                        feed_entry["updated"],
                        feed_entry["author"],
                        datetime.datetime.now(),
                        content,
                        source["id"],
                        [],
                    )

                    news_items.append(news_item)

            self.publish(news_items, source)
        except Exception:
            logger.exception()
            logger.collector_exception(source, "Could not collect ATOM Feed")
