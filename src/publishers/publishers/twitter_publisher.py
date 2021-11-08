from base64 import b64decode
import tweepy

from .base_publisher import BasePublisher
from schema.parameter import Parameter, ParameterType


class TWITTERPublisher(BasePublisher):
    type = "TWITTER_PUBLISHER"
    name = "Twitter Publisher"
    description = "Publisher for publishing to Twitter account"

    parameters = [
        Parameter(0, "TWITTER_API_KEY", "Twitter API key", "API key of Twitter account", ParameterType.STRING),
        Parameter(0, "TWITTER_API_KEY_SECRET", "Twitter API key secret", "API key secret of Twitter account",
                  ParameterType.STRING),
        Parameter(0, "TWITTER_ACCESS_TOKEN", "Twitter access token", "Twitter access token of Twitter account",
                  ParameterType.STRING),
        Parameter(0, "TWITTER_ACCESS_TOKEN_SECRET", "Twitter access token secret",
                  "Twitter access token secret of Twitter account", ParameterType.STRING)
    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):

        try:
            api_key = publisher_input.parameter_values_map['TWITTER_API_KEY']
            api_key_secret = publisher_input.parameter_values_map['TWITTER_API_KEY_SECRET']
            access_token = publisher_input.parameter_values_map['TWITTER_ACCESS_TOKEN']
            access_token_secret = publisher_input.parameter_values_map['TWITTER_ACCESS_TOKEN_SECRET']

            auth = tweepy.OAuthHandler(api_key, api_key_secret)
            auth.set_access_token(access_token, access_token_secret)

            api = tweepy.API(auth)

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True)

            if len(bytes_data) <= 240:
                api.update_status(bytes_data)
        except Exception as error:
            BasePublisher.print_exception(self, error)
