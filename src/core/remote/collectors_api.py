import requests


class CollectorsApi:

    def __init__(self, api_url, api_key):
        self.api_url = api_url
        if self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
        self.api_key = api_key
        self.headers = {'Authorization': 'Bearer ' + self.api_key}

    def get_collectors_info(self, id):
        response = requests.post(self.api_url + "/api/v1/collectors", headers=self.headers, json={
            'id': id
        })
        return response.json(), response.status_code

    def refresh_collector(self, collector_type):
        response = requests.put(self.api_url + "/api/v1/collectors/" + collector_type, headers=self.headers)
        return response.status_code
