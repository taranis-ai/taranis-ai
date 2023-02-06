import os
from base64 import b64encode
import jinja2

from .base_presenter import BasePresenter


class HTMLPresenter(BasePresenter):
    type = "HTML_PRESENTER"
    name = "HTML Presenter"
    description = "Presenter for generating html documents"

    def generate(self, presenter_input):
        try:
            head, tail = os.path.split(presenter_input.parameter_values_map["HTML_TEMPLATE_PATH"])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            output_text = env.get_template(tail).render(data=input_data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode("UTF-8")

            return {"mime_type": "text/html", "data": data}
        except Exception as error:
            BasePresenter.print_exception(self, error)
