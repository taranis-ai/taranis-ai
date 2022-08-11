import requests


class CollectorsApi:
    def __init__(self, api_url, api_key):
        self.api_url = api_url[:-1] if api_url.endswith("/") else api_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_collectors_info(self, collector_id):
        response = requests.post(f"{self.api_url}/api/v1/collectors", headers=self.headers, json={"id": collector_id})

        return response.json(), response.status_code

    def refresh_collector(self, collector_type):
        response = requests.put(f"{self.api_url}/api/v1/collectors/{collector_type}", headers=self.headers)

        return response.status_code
