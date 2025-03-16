import base64
import requests

from .base_publisher import BasePublisher


class WORDPRESSPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "WORDPRESS_PUBLISHER"
        self.name = "Wordpress Publisher"
        self.description = "Publisher for publishing on Wordpress webpage"

    def publish(self, publisher, product, rendered_product):
        parameters = publisher.get("parameters")

        user = parameters.get("WP_USER")
        python_app_secret = parameters.get("WP_PYTHON_APP_SECRET")
        main_wp_url = parameters.get("WP_URL")

        data_string = f"{user}:{python_app_secret}"

        token = base64.b64encode(data_string.encode())

        headers = {"Authorization": "Basic " + token.decode("utf-8")}

        bytes_data = rendered_product.data.decode("utf-8")

        post = {"title": product.get("title"), "status": "publish", "content": bytes_data}

        response = requests.post(f"{main_wp_url}/index.php/wp-json/wp/v2/posts", headers=headers, json=post, timeout=60)
        return response.text
