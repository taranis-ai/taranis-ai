import datetime
import hashlib
import uuid

import feedparser
import urllib
from urllib.request import ProxyHandler
import requests
from bs4 import BeautifulSoup
import dateparser

from taranisng.schema.news_item import NewsItemData
from taranisng.schema.parameter import Parameter, ParameterType
from .base_collector import BaseCollector


class RSSCollector(BaseCollector):
    type = "RSS_COLLECTOR"
    name = "RSS Collector"
    description = "Collector for gathering data from RSS feeds"

    parameters = [
        Parameter(0, "FEED_URL", "Feed URL", "Full url for RSS feed", ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Type of user agent", ParameterType.STRING)
    ]

    parameters.extend(BaseCollector.parameters)

    news_items = []

    def collect(self, source):

        feed_url = source.parameter_values['FEED_URL']
        interval = source.parameter_values['REFRESH_INTERVAL']

        user_agent = source.parameter_values['USER_AGENT']
        if user_agent:
            feedparser.USER_AGENT = user_agent
            user_agent_headers = {'User-Agent': user_agent}
        else:
            user_agent_headers = { }

        proxies = {}
        if 'PROXY_SERVER' in source.parameter_values:
            proxy_server = source.parameter_values['PROXY_SERVER']

            if proxy_server.startswith('https://'):
                proxies['https'] = proxy_server[8:].rstrip('/')
            elif proxy_server.startswith('http://'):
                proxies['http'] = proxy_server[7:].rstrip('/')
            else:
                proxies['http'] = proxy_server.rstrip('/')


        try:
            if proxies:
                proxy = ProxyHandler(proxies)
                feed = feedparser.parse(feed_url, handlers = [proxy])
            else:
                feed = feedparser.parse(feed_url)

            news_items = []

            for feed_entry in feed['entries']:

                for key in ['author', 'published', 'title', 'description', 'link']:
                    if not feed_entry.has_key(key):
                        feed_entry[key] = ''

                limit = BaseCollector.history(interval)
                published = feed_entry['published']
                published = dateparser.parse(published, settings={'DATE_ORDER': 'DMY'})

                # if published > limit: TODO: uncomment after testing, we need some initial data now
                link_for_article = feed_entry['link']

                if proxies:
                    page = requests.get(link_for_article, headers=user_agent_headers, proxies=proxies)
                else:
                    page = requests.get(link_for_article, headers=user_agent_headers)

                html_content = page.text
                soup = BeautifulSoup(html_content, features='html.parser')

                content = ''

                if html_content:
                    content_text = [p.text.strip() for p in soup.findAll('p')]
                    replaced_str = '\xa0'
                    if replaced_str:
                        content = [w.replace(replaced_str, ' ') for w in content_text]
                        content = ' '.join(content)

                for_hash = feed_entry['author'] + feed_entry['title'] + feed_entry['link']

                news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(for_hash.encode()).hexdigest(),
                                         feed_entry['title'], feed_entry['description'], feed_url, feed_entry['link'],
                                         feed_entry['published'], feed_entry['author'], datetime.datetime.now(),
                                         content, source.id, [])

                news_items.append(news_item)

            BaseCollector.publish(news_items, source)

        except Exception as error:
            BaseCollector.print_exception(source, error)
