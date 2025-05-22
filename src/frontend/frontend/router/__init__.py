from flask import Flask
from swagger_ui import api_doc

from frontend.config import Config
from frontend.router import base, admin, admin_settings, user


def init(app: Flask):
    doc_url_prefix = f"{Config.APPLICATION_ROOT}doc" if Config.APPLICATION_ROOT == "/" else f"{Config.APPLICATION_ROOT}/doc"
    api_doc(app, config_path="frontend/static/assets/openapi3_1.yaml", url_prefix=doc_url_prefix, editor=False, blueprint_name="api_doc")
    base.init(app)
    user.init(app)
    admin.init(app)
    admin_settings.init(app)
