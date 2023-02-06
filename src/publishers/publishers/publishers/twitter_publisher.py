from base64 import b64decode
import tweepy

from .base_publisher import BasePublisher


class TWITTERPublisher(BasePublisher):
    type = "TWITTER_PUBLISHER"
    name = "Twitter Publisher"
    description = "Publisher for publishing to Twitter account"

    def publish(self, publisher_input):

        try:
            api_key = publisher_input.parameter_values_map["TWITTER_API_KEY"]
            api_key_secret = publisher_input.parameter_values_map["TWITTER_API_KEY_SECRET"]
            access_token = publisher_input.parameter_values_map["TWITTER_ACCESS_TOKEN"]
            access_token_secret = publisher_input.parameter_values_map["TWITTER_ACCESS_TOKEN_SECRET"]

            auth = tweepy.OAuthHandler(api_key, api_key_secret)
            auth.set_access_token(access_token, access_token_secret)

            api = tweepy.API(auth)

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            if len(bytes_data) <= 240:
                api.update_status(bytes_data)
        except Exception as error:
            BasePublisher.print_exception(self, error)
