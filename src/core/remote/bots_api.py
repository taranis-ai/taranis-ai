import requests


class BotsApi:

    def __init__(self, api_url, api_key):
        self.api_url = api_url
        if self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
        self.api_key = api_key
        self.headers = {'Authorization': 'Bearer ' + self.api_key}

    def get_bots_info(self):
        response = requests.get(self.api_url + "/api/v1/bots", headers=self.headers)
        return response.json(), response.status_code
