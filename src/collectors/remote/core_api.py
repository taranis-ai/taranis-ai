import logging
import os
import urllib
import requests

logger = logging.getLogger('gunicorn.error')
logger.level = logging.DEBUG


class CoreApi:
    api_url = os.getenv('TARANIS_NG_CORE_URL')
    if api_url.endswith("/"):
        api_url = api_url[:-1]
    api_key = os.getenv('API_KEY')
    headers = {'Authorization': 'Bearer ' + api_key}

    @classmethod
    def get_osint_sources(cls, collector_type):
        id = ''
        config_file = os.getenv('COLLECTOR_CONFIG_FILE')
        try:
            with open(config_file, 'r') as file:
                id = file.read().strip()
        except Exception as ex:
            logger.debug(ex)
            return 'Cannot read collector config file.', 0

        try:
            response = requests.get(cls.api_url + '/api/v1/collectors/' + urllib.parse.quote(id) + '/osint-sources?api_key=' + urllib.parse.quote(cls.api_key) + '&collector_type=' + urllib.parse.quote(collector_type),
                                     headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            logger.debug(ex)
            return None, 400

    @classmethod
    def update_collector_status(cls):
        id = ''
        config_file = os.getenv('COLLECTOR_CONFIG_FILE')
        try:
            with open(config_file, 'r') as file:
                id = file.read().strip()
        except Exception as ex:
            logger.debug(ex)
            return 'Cannot read collector config file.', 0

        try:
            response = requests.get(cls.api_url + '/api/v1/collectors/' + urllib.parse.quote(id),
                                     headers=cls.headers)
            return response.json(), response.status_code
        except Exception as ex:
            logger.debug(ex)
            return ex, 400

    @classmethod
    def add_news_items(cls, news_items):
        try:
            response = requests.post(cls.api_url + '/api/v1/collectors/news-items', json=news_items,
                                     headers=cls.headers)
            return response.status_code
        except Exception as ex:
            logger.debug(ex)
            return None, 400
