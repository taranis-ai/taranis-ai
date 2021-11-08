import datetime
import hashlib
import uuid
import time
from slackclient import SlackClient
import socket

from .base_collector import BaseCollector
from schema.news_item import NewsItemData
from schema.parameter import Parameter, ParameterType


class SlackCollector(BaseCollector):
    type = "SLACK_COLLECTOR"
    name = "Slack Collector"
    description = "Collector for gathering data from Slack"

    parameters = [
        Parameter(0, "SLACK_API_TOKEN", "Slack API token", "API token for Slack authentication.", ParameterType.STRING),
        Parameter(0, "WORKSPACE_CHANNELS_ID", "Collected workspace's channels ID", "Channels which will be collected.",
                  ParameterType.STRING)
    ]

    parameters.extend(BaseCollector.parameters)

    def collect(self, source):

        news_items = []

        proxy_server = source.parameter_values['PROXY_SERVER']

        if proxy_server:

            server = 'https://slack.com'
            port = 443

            server_proxy = proxy_server.rsplit(':', 1)[0]
            server_proxy_port = proxy_server.rsplit(':', 1)[-1]

            try:
                proxy = (str(server_proxy), int(server_proxy_port))
                connection = f'CONNECT {server}:{port} HTTP/1.0\r\nConnection: close\r\n\r\n'

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(proxy)
                s.send(str.encode(connection))
                s.recv(4096)
            except Exception:
                print('OSINTSource ID: ' + source.id)
                print('OSINTSource name: ' + source.name)
                print('Proxy connection failed')

        slack_client = SlackClient(source.parameter_values['SLACK_API_TOKEN'])

        if slack_client.rtm_connect():

            while True:
                try:
                    data = slack_client.rtm_read()

                    if data:
                        for item in data:

                            ids = source.parameter_values['WORKSPACE_CHANNELS_ID'].replace(' ', '')
                            channels_list = ids.split(',')

                            if item['type'] == 'message' and item['channel'] in channels_list:
                                published = time.ctime(float(item["ts"]))
                                content = item['text']
                                preview = item['text'][:500]

                                user = item['user']
                                user_name = slack_client.api_call("users.info", user=user)
                                author = user_name['user']['real_name']

                                channel_id = item['channel']
                                channel_name = slack_client.api_call("channels.info", channel=channel_id)
                                channel = channel_name['channel']['name']

                                team = item['team']
                                team_name = slack_client.api_call("team.info", team=team)
                                workspace = team_name['team']['name']

                                title = 'Slack post from workspace ' + workspace + ' and channel ' + channel
                                link = ''
                                url = ''

                                for_hash = author + channel + content

                                news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(for_hash.encode()).hexdigest(),
                                                         title, preview, url, link, published, author,
                                                         datetime.datetime.now(), content, source.id, [])

                                news_items.append(news_item)

                        BaseCollector.publish(news_items, source)

                        time.sleep(1)
                except KeyError:
                    print('Deleted message')
                    pass
        else:
            print('OSINTSource ID: ' + source.id)
            print('OSINTSource name: ' + source.name)
            print('ERROR')
