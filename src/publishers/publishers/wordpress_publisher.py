import base64
from base64 import b64decode
from datetime import datetime
import requests

from .base_publisher import BasePublisher
from schema.parameter import Parameter, ParameterType


class WORDPRESSPublisher(BasePublisher):
    type = "WORDPRESS_PUBLISHER"
    name = "Wordpress Publisher"
    description = "Publisher for publishing on Wordpress webpage"

    parameters = [
        Parameter(0, "WP_URL", "Wordpress URL address", "URL address of wordpress webpage", ParameterType.STRING),
        Parameter(0, "WP_USER", "Username of wordpress editor", "Post editor's username", ParameterType.STRING),
        Parameter(0, "WP_PYTHON_APP_SECRET", "Secret key of application",
                  "Secret key created in Wordpress for Python application", ParameterType.STRING)
    ]

    parameters.extend(BasePublisher.parameters)

    def publish(self, publisher_input):

        try:
            user = publisher_input.parameter_values_map['WP_USER']
            python_app_secret = publisher_input.parameter_values_map['WP_PYTHON_APP_SECRET']
            main_wp_url = publisher_input.parameter_values_map['WP_URL']

            data_string = user + ':' + python_app_secret

            token = base64.b64encode(data_string.encode())

            headers = {'Authorization': 'Basic ' + token.decode('utf-8')}

            data = publisher_input.data[:]

            bytes_data = b64decode(data, validate=True).decode("utf-8")

            now = datetime.now()
            title = 'Report from TaranisNG on ' + now.strftime("%d.%m.%Y") + ' at ' + now.strftime("%H:%M")

            post = {'title': title,
                    'status': 'publish',
                    'content': bytes_data
                    }

            requests.post(main_wp_url + '/index.php/wp-json/wp/v2/posts', headers=headers, json=post)
        except Exception as error:
            BasePublisher.print_exception(self, error)
