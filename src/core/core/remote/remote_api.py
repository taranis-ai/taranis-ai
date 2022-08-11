import requests


class RemoteApi:
    def __init__(self, api_url, access_key):
        self.api_url = api_url
        if self.api_url.endswith("/"):
            self.api_url = self.api_url[:-1]
        self.access_key = access_key
        self.headers = {"Authorization": f"Bearer {self.access_key}"}

    def connect(self):
        try:
            response = requests.get(f"{self.api_url}/api/v1/remote/connect", headers=self.headers)

            return response.json(), response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503

    def disconnect(self):
        try:
            requests.get(f"{self.api_url}/api/v1/remote/disconnect", headers=self.headers)
        except requests.exceptions.ConnectionError:
            return {}, 503

    def get_news_items(self):
        try:
            response = requests.get(f"{self.api_url}/api/v1/remote/sync-news-items", headers=self.headers)

            return response.json(), response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503

    def confirm_news_items_sync(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/remote/sync-news-items",
                headers=self.headers,
                json=data,
            )

            return response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503

    def get_report_items(self):
        try:
            response = requests.get(f"{self.api_url}/api/v1/remote/sync-report-items", headers=self.headers)

            return response.json(), response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503

    def confirm_report_items_sync(self, data):
        try:
            response = requests.put(
                f"{self.api_url}/api/v1/remote/sync-report-items",
                headers=self.headers,
                json=data,
            )

            return response.status_code
        except requests.exceptions.ConnectionError:
            return {}, 503
