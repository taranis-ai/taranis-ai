import os
from base64 import b64encode

import jinja2

from presenters.base_presenter import BasePresenter
from taranisng.schema.parameter import Parameter, ParameterType


class MISPPresenter(BasePresenter):
    type = "MISP_PRESENTER"
    name = "MISP Presenter"
    description = "Presenter for generating MISP platform"

    parameters = [
        Parameter(0, "MISP_TEMPLATE_PATH", "MISP template with its path", "Path of MISP template file",
                  ParameterType.STRING)
    ]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):

        try:
            head, tail = os.path.split(presenter_input.parameter_values_map['MISP_TEMPLATE_PATH'])

            data = BasePresenter.generate_report_data_map(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            output_text = env.get_template(tail).render(data=data).encode()

            base64_bytes = b64encode(output_text)

            data = base64_bytes.decode('UTF-8')

            presenter_output = {
                'mime_type': 'application/json',
                'data': data
            }

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
