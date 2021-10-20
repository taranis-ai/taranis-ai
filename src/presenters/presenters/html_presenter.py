import os
from base64 import b64encode

import jinja2

from presenters.base_presenter import BasePresenter
from taranisng.schema.parameter import Parameter, ParameterType


class HTMLPresenter(BasePresenter):
    type = "HTML_PRESENTER"
    name = "HTML Presenter"
    description = "Presenter for generating html documents"

    parameters = [
        Parameter(0, "HTML_TEMPLATE_PATH", "HTML template with its path", "Path of html template file",
                  ParameterType.STRING)
    ]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):

        try:
            head, tail = os.path.split(presenter_input.parameter_values_map['HTML_TEMPLATE_PATH'])

            data = BasePresenter.generate_report_data_map(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            output_text = env.get_template(tail).render(data=data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode('UTF-8')

            presenter_output = {
                'mime_type': 'text/html',
                'data': data
            }
            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
