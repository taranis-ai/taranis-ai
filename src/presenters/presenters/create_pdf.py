import yaml
import pdfkit
import jinja2
import os
import glob
# import datetime
from flask import send_file
from base64 import b64encode
import json

TEMPLATE_HEADER_FILE = 'sw_header.html'
TEMPLATE_BODY_FILE = 'sw_body.html'
TEMPLATE_FOOTER_FILE = 'sw_footer.html'
DATA_FILE = 'data/data.yml'
TEMPORARY_DIRECTORY = 'tmp/'
OUTPUT_BODY_HTML = TEMPORARY_DIRECTORY + 'body.html'
OUTPUT_HEADER_HTML = TEMPORARY_DIRECTORY + 'header.html'
OUTPUT_FOOTER_HTML = TEMPORARY_DIRECTORY + 'footer.html'
# OUTPUT_PDF = TEMPORARY_DIRECTORY + 'security_warning_' + datetime.datetime.now().strftime("%d-%m-%Y_%H:%M") + '.pdf'
OUTPUT_PDF = TEMPORARY_DIRECTORY + 'output.pdf'


def get_data():
    with open(DATA_FILE, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def get_templates():
    template_loader = jinja2.FileSystemLoader(searchpath="templates/sw")
    template_env = jinja2.Environment(loader=template_loader)
    return template_env


def generate_html_output():
    data = get_data()
    template = get_templates()

    body = template.get_template(TEMPLATE_BODY_FILE)
    output_text = body.render(**data)
    with open(OUTPUT_BODY_HTML, 'w') as output_file:
        output_file.write(output_text)

    header = template.get_template(TEMPLATE_HEADER_FILE)
    output_text = header.render(**data)
    with open(OUTPUT_HEADER_HTML, 'w') as output_file:
        output_file.write(output_text)

    footer = template.get_template(TEMPLATE_FOOTER_FILE)
    output_text = footer.render(**data)
    with open(OUTPUT_FOOTER_HTML, 'w') as output_file:
        output_file.write(output_text)


def generate_pdf():
    if not os.path.exists(TEMPORARY_DIRECTORY):
        os.mkdir(TEMPORARY_DIRECTORY)

    generate_html_output()

    options = {
        'dpi': 500,
        'page-size': 'A4',
        'margin-top': '1.55in',
        'margin-right': '0.75in',
        'margin-bottom': '1.55in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'header-html': OUTPUT_HEADER_HTML,
        'footer-html': OUTPUT_FOOTER_HTML,
        'custom-header': [
            ('Accept-Encoding', 'gzip')
        ],
        'no-outline': None,
    }

    pdfkit.from_file(input=OUTPUT_BODY_HTML, output_path=OUTPUT_PDF, options=options)

    files = glob.glob(TEMPORARY_DIRECTORY + '*.html')
    for html_file in files:
        os.remove(html_file)

    return send_file(open(OUTPUT_PDF, 'rb'), mimetype='application/pdf')


def create_binary_data():

    generate_pdf()

    encoding = 'UTF-8'
    filename = OUTPUT_PDF

    with open(filename, 'rb') as open_file:
        byte_content = open_file.read()

    base64_bytes = b64encode(byte_content)

    base64_string = base64_bytes.decode(encoding)

    data = {
        'type': 'File',
        'title': 'Security Warning',
        'file': {
            'encoding': 'base64',
            'content-type': 'application/pdf',
            'data': base64_string
        }
    }

    json_data = json.dumps(data, indent=2)

    return json.loads(json_data)
