import os
from base64 import b64encode
import jinja2

from .base_presenter import BasePresenter
from schema.parameter import Parameter, ParameterType


class TEXTPresenter(BasePresenter):
    type = "TEXT_PRESENTER"
    name = "TEXT Presenter"
    description = "Presenter for generating text documents"

    parameters = [
        Parameter(0, "TEXT_TEMPLATE_PATH", "TEXT template with its path", "Path of text template file",
                  ParameterType.STRING)
    ]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):

        try:
            head, tail = os.path.split(presenter_input.parameter_values_map['TEXT_TEMPLATE_PATH'])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            output_text = env.get_template(tail).render(data=input_data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode('UTF-8')

            presenter_output = {
                'mime_type': 'text/plain',
                'data': data
            }

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
