import requests


class CollectorsApi:

    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {'Authorization': 'Bearer ' + self.api_key}

    def get_collectors_info(self):
        response = requests.get(self.api_url + "/api/v1/collectors", headers=self.headers)
        return response.json(), response.status_code
