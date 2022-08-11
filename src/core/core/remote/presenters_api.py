import requests


class PresentersApi:
    def __init__(self, api_url, api_key):
        self.api_url = api_url
        if self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_presenters_info(self):
        response = requests.get(f"{self.api_url}/api/v1/presenters", headers=self.headers)

        return response.json(), response.status_code

    def generate(self, data):
        response = requests.post(f"{self.api_url}/api/v1/presenters", json=data, headers=self.headers)

        return response.json(), response.status_code
