import datetime
import hashlib
import uuid
import tweepy

from .base_collector import BaseCollector
from schema.news_item import NewsItemData
from schema.parameter import Parameter, ParameterType


class TwitterCollector(BaseCollector):
    type = "TWITTER_COLLECTOR"
    name = "Twitter Collector"
    description = "Collector for gathering data from Twitter"

    parameters = [
        Parameter(0, "TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
        Parameter(0, "TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account",
                  ParameterType.STRING),
        Parameter(0, "TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account",
                  ParameterType.STRING),
        Parameter(0, "TWITTER_ACCESS_TOKEN_SECRET", "Twitter access token secret",
                  "Twitter access token secret of Twitter account", ParameterType.STRING),
        Parameter(0, "SEARCH_KEYWORDS", "Search by keywords", "Search tweets by keywords", ParameterType.STRING),
        Parameter(0, "SEARCH_HASHTAGS", "Search by hashtags", "Search tweets by hashtags", ParameterType.STRING),
        Parameter(0, "NUMBER_OF_TWEETS", "Number of tweets", "How many tweets will be provided", ParameterType.NUMBER)
    ]

    parameters.extend(BaseCollector.parameters)

    def collect(self, source):

        try:
            news_items = []
            attributes = []

            search_keywords = source.parameter_values['SEARCH_KEYWORDS'].replace(' ', '')
            keywords_list = search_keywords.split(',')

            search_hashtags = source.parameter_values['SEARCH_HASHTAGS'].replace(' ', '')
            hashtags_list = search_hashtags.split(',')

            number_of_tweets = source.parameter_values['NUMBER_OF_TWEETS']

            twitter_api_key = source.parameter_values['TWITTER_API_KEY']
            twitter_api_key_secret = source.parameter_values['TWITTER_API_KEY_SECRET']
            twitter_access_token = source.parameter_values['TWITTER_ACCESS_TOKEN']
            twitter_access_token_secret = source.parameter_values['TWITTER_ACCESS_TOKEN_SECRET']

            proxy_server = source.parameter_values['PROXY_SERVER']

            auth = tweepy.OAuthHandler(twitter_api_key, twitter_api_key_secret)
            auth.set_access_token(twitter_access_token, twitter_access_token_secret)

            if proxy_server:
                proxy = 'socks5://' + proxy_server
                api = tweepy.API(auth, proxy=str(proxy), wait_on_rate_limit=True)
            else:
                api = tweepy.API(auth, wait_on_rate_limit=True)

            if number_of_tweets == '':
                number_of_tweets = 100

            if search_keywords:
                public_tweets = tweepy.Cursor(api.search, q=keywords_list).items(int(number_of_tweets))
            elif search_hashtags:
                public_tweets = tweepy.Cursor(api.search, q=hashtags_list).items(int(number_of_tweets))
            else:
                public_tweets = api.home_timeline(count=number_of_tweets)

            interval = source.parameter_values["REFRESH_INTERVAL"]

            limit = BaseCollector.history(interval)

            for tweet in public_tweets:

                time_to_collect = tweet.created_at

                if time_to_collect > limit:
                    tweet_id = tweet.id_str
                    link = f'https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}'
                    author = tweet.author.name
                    preview = tweet.text.encode("utf-8")
                    published = tweet.created_at
                    title = 'Twitter post from ' + '@' + author
                    content = ''
                    url = ''

                    for_hash = author + tweet_id + str(preview)

                    news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(for_hash.encode()).hexdigest(), title,
                                             preview, url, link, published, author, datetime.datetime.now(),
                                             content, source.id, attributes)

                    news_items.append(news_item)

            BaseCollector.publish(news_items, source)
        except Exception as error:
            BaseCollector.print_exception(source, error)
