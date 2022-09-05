import datetime
import hashlib
import uuid
import traceback
import re
import socks
import feedparser
import requests
from sockshandler import SocksiPyHandler
from bs4 import BeautifulSoup
import dateutil.parser as dateparser

from .base_collector import BaseCollector
from collectors.managers.log_manager import logger
from shared.schema.news_item import NewsItemData
from shared.schema.parameter import Parameter, ParameterType


class RSSCollector(BaseCollector):
    type = "RSS_COLLECTOR"
    name = "RSS Collector"
    description = "Collector for gathering data from RSS feeds"

    parameters = [
        Parameter(0, "FEED_URL", "Feed URL", "Full url for RSS feed", ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING),
        Parameter(0, "CONTENT_LOCATION", "Content Location", "Location of the 'content' Field", ParameterType.STRING),
    ]

    parameters.extend(BaseCollector.parameters)

    news_items = []

    def get_proxy_handler(self, proxy_server: str):
        proxy = re.search(
            r"^(http|https|socks4|socks5)://([a-zA-Z0-9\-\.\_]+):(\d+)/?$",
            proxy_server,
        )
        if proxy:
            from urllib.request import ProxyHandler

            scheme, host, port = proxy.groups()
            # classic HTTP/HTTPS proxy
            if scheme in ["http", "https"]:
                return ProxyHandler(
                    {"http": f"{scheme}://{host}:{port}", "https": f"{scheme}://{host}:{port}", "ftp": f"{scheme}://{host}:{port}"}
                )

            elif scheme == "socks4":
                return SocksiPyHandler(socks.SOCKS4, host, int(port))
            elif scheme == "socks5":
                return SocksiPyHandler(socks.SOCKS5, host, int(port))
        return None

    def get_article_content(self, link_for_article: str, headers: dict, proxies: dict) -> str:
        try:
            html_content, status = requests.get(link_for_article, headers=headers, proxies=proxies)
        except Exception:
            return ""

        return "" if status != 200 else html_content

    def parse_article_content(self, html_content: str, feed_entry: list, content_location: str = "p") -> str:
        if "_" in content_location:
            cl_list = content_location.split("_")
            if cl_list[0] == "xml" and cl_list[1] in feed_entry:
                return feed_entry[cl_list[1]]

        soup = BeautifulSoup(html_content, features="html.parser")
        if html_content:
            content_text = [p.text.strip() for p in soup.findAll(content_location)]
            if replaced_str := "\xa0":
                content = [w.replace(replaced_str, " ") for w in content_text]
                return " ".join(content)
        return ""

    def collect(self, source):
        feed_url = source.parameter_values["FEED_URL"]
        # interval = source.parameter_values["REFRESH_INTERVAL"]

        logger.log_collector_activity("rss", source.id, f"Starting collector for url: {feed_url}")

        user_agent = source.parameter_values["USER_AGENT"]
        if user_agent:
            feedparser.USER_AGENT = user_agent

        proxy_handler = self.get_proxy_handler(source.parameter_values.get("PROXY_SERVER"))

        try:
            if proxy_handler:
                feed = feedparser.parse(feed_url, handlers=[proxy_handler])
                proxies = proxy_handler.proxies
            else:
                feed = feedparser.parse(feed_url)
                proxies = None

            logger.log_collector_activity("rss", source.id, f'RSS returned feed with {len(feed["entries"])} entries')

            news_items = []

            for feed_entry in feed["entries"]:

                for key in ["author", "published", "title", "description", "link"]:
                    if key not in feed_entry:
                        feed_entry[key] = ""

                # limit = BaseCollector.history(interval)
                published = feed_entry["published"]
                published = dateparser.parse(published)

                # if published > limit: TODO: uncomment after testing, we need some initial data now
                logger.log_collector_activity("rss", source.id, f"Processing entry [{feed_entry['link']}]")

                content = self.get_article_content(link_for_article=feed_entry["link"], headers={"User-Agent": user_agent}, proxies=proxies)

                content = self.parse_article_content(
                    html_content=content, feed_entry=feed_entry, content_location=source.parameter_values["CONTENT_LOCATION"]
                )

                for_hash = feed_entry["author"] + feed_entry["title"] + feed_entry["link"]

                news_item = NewsItemData(
                    uuid.uuid4(),
                    hashlib.sha256(for_hash.encode()).hexdigest(),
                    feed_entry["title"],
                    feed_entry["description"],
                    feed_url,
                    feed_entry["link"],
                    feed_entry["published"],
                    feed_entry["author"],
                    datetime.datetime.now(),
                    content,
                    source.id,
                    [],
                )

                news_items.append(news_item)

            self.publish(news_items, source)

        except Exception as error:
            logger.log_collector_activity("rss", source.id, "RSS collection exceptionally failed")
            BaseCollector.print_exception(source, error)
            logger.log_debug(traceback.format_exc())

        logger.log_debug(f"{self.type} collection finished.")
