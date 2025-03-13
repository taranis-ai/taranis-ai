import tweepy

from .base_publisher import BasePublisher


class TWITTERPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "TWITTER_PUBLISHER"
        self.name = "Twitter Publisher"
        self.description = "Publisher for publishing to Twitter account"

    def publish(self, publisher, product, rendered_product):
        parameters = publisher.get("parameters")

        api_key = parameters.get("TWITTER_API_KEY")
        api_key_secret = parameters.get("TWITTER_API_KEY_SECRET")
        access_token = parameters.get("TWITTER_ACCESS_TOKEN")
        access_token_secret = parameters.get("TWITTER_ACCESS_TOKEN_SECRET")

        auth = tweepy.OAuthHandler(api_key, api_key_secret)
        auth.set_access_token(access_token, access_token_secret)

        api = tweepy.API(auth)

        bytes_data = rendered_product.data.decode("utf-8")

        if len(bytes_data) > 240:
            raise ValueError("Tweet is too long")

        return api.update_status(bytes_data)
