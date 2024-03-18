from requests import Response


class Product:
    def __init__(self, response: Response):
        self.data: bytes = response.content
        self.mime_type: str = response.headers["Content-Type"]
