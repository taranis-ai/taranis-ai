import datetime
import hashlib
import uuid
import tweepy

from .base_collector import BaseCollector
from worker.log import logger


class TwitterCollector(BaseCollector):
    type = "TWITTER_COLLECTOR"
    name = "Twitter Collector"
    description = "Collector for gathering data from Twitter"

    def collect(self, source):
        try:
            news_items = []
            attributes = []

            search_keywords = source["parameters"]["SEARCH_KEYWORDS"].replace(" ", "")
            keywords_list = search_keywords.split(",")

            search_hashtags = source["parameters"]["SEARCH_HASHTAGS"].replace(" ", "")
            hashtags_list = search_hashtags.split(",")

            number_of_tweets = source["parameters"]["NUMBER_OF_TWEETS"]

            twitter_api_key = source["parameters"]["TWITTER_API_KEY"]
            twitter_api_key_secret = source["parameters"]["TWITTER_API_KEY_SECRET"]
            twitter_access_token = source["parameters"]["TWITTER_ACCESS_TOKEN"]
            twitter_access_token_secret = source["parameters"]["TWITTER_ACCESS_TOKEN_SECRET"]

            proxy_server = source["parameters"]["PROXY_SERVER"]

            auth = tweepy.OAuthHandler(twitter_api_key, twitter_api_key_secret)
            auth.set_access_token(twitter_access_token, twitter_access_token_secret)

            if proxy_server:
                proxy = "socks5://" + proxy_server
                api = tweepy.API(auth, proxy=str(proxy), wait_on_rate_limit=True)
            else:
                api = tweepy.API(auth, wait_on_rate_limit=True)

            if number_of_tweets == "":
                number_of_tweets = 100

            if search_keywords:
                public_tweets = tweepy.Cursor(api.search, q=keywords_list).items(int(number_of_tweets))
            elif search_hashtags:
                public_tweets = tweepy.Cursor(api.search, q=hashtags_list).items(int(number_of_tweets))
            else:
                public_tweets = api.home_timeline(count=number_of_tweets)

            interval = source["parameters"]["REFRESH_INTERVAL"]

            limit = BaseCollector.history(interval)

            for tweet in public_tweets:
                time_to_collect = tweet.created_at

                if time_to_collect > limit:
                    tweet_id = tweet.id_str
                    link = f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
                    author = tweet.author.name
                    preview = tweet.text.encode("utf-8")
                    published = tweet.created_at
                    title = f"Twitter post from @{author}"
                    content = ""
                    url = ""

                    for_hash = author + tweet_id + str(preview)

                    news_item = {
                        "id": str(uuid.uuid4()),
                        "hash": hashlib.sha256(for_hash.encode()).hexdigest(),
                        "title": title,
                        "review": preview,
                        "source": url,
                        "link": link,
                        "published": published,
                        "author": author,
                        "collected": datetime.datetime.now(),
                        "content": content,
                        "osint_source_id": source["id"],
                        "attributes": [],
                    }

                    news_items.append(news_item)

            self.publish(news_items, source)
        except Exception:
            logger.exception()
            logger.error(f"Could not collect Tweeets {source['id']}")
