import datetime
import os
import tempfile
from base64 import b64encode
import jinja2
import pdfkit

from .base_presenter import BasePresenter
from schema.parameter import Parameter, ParameterType


class PDFPresenter(BasePresenter):
    type = "PDF_PRESENTER"
    name = "PDF Presenter"
    description = "Presenter for generating PDF documents"

    parameters = [
        Parameter(0, "HEADER_TEMPLATE_PATH", "Header template path", "Path of header template file",
                  ParameterType.STRING),
        Parameter(0, "BODY_TEMPLATE_PATH", "Body template path", "Path of body template file",
                  ParameterType.STRING),
        Parameter(0, "FOOTER_TEMPLATE_PATH", "Footer template path", "Path of footer template file",
                  ParameterType.STRING)
    ]

    parameters.extend(BasePresenter.parameters)

    def generate(self, presenter_input):

        try:
            temporary_directory = tempfile.gettempdir() + "/"
            output_body_html = temporary_directory + 'pdf_body.html'
            output_pdf = temporary_directory + 'pdf_report__' + datetime.datetime.now().strftime(
                "%d-%m-%Y_%H:%M") + '.pdf'

            pdf_header_template = presenter_input.parameter_values_map['HEADER_TEMPLATE_PATH']
            pdf_footer_template = presenter_input.parameter_values_map['FOOTER_TEMPLATE_PATH']
            head, tail = os.path.split(presenter_input.parameter_values_map['BODY_TEMPLATE_PATH'])

            input_data = BasePresenter.generate_input_data(presenter_input)

            env = jinja2.Environment(loader=jinja2.FileSystemLoader(head))

            body = env.get_template(tail)
            output_text = body.render(data=input_data)
            with open(output_body_html, 'w') as output_file:
                output_file.write(output_text)

            if not os.path.exists(temporary_directory):
                os.mkdir(temporary_directory)

            options = {
                'dpi': 500,
                'page-size': 'A4',
                'margin-top': '1.55in',
                'margin-right': '0.75in',
                'margin-bottom': '1.55in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'header-html': pdf_header_template,
                'footer-html': pdf_footer_template,
                'custom-header': [
                    ('Accept-Encoding', 'gzip')
                ],
                'no-outline': None,
                'enable-local-file-access': None
            }

            pdfkit.from_file(input=output_body_html, output_path=output_pdf, options=options)

            encoding = 'UTF-8'
            file = output_pdf

            with open(file, 'rb') as open_file:
                byte_content = open_file.read()

            base64_bytes = b64encode(byte_content)

            data = base64_bytes.decode(encoding)

            presenter_output = {
                'mime_type': 'application/pdf',
                'data': data
            }

            os.remove(output_body_html)
            os.remove(file)

            return presenter_output
        except Exception as error:
            BasePresenter.print_exception(self, error)
