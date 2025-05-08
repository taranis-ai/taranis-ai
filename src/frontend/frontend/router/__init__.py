from flask import Flask
from swagger_ui import api_doc

from frontend.config import Config
from frontend.router import base, admin, admin_settings


def init(app: Flask):
    api_doc(app, config_url=f"{Config.TARANIS_CORE_URL}/static/openapi3_1.yaml", url_prefix=f"{Config.APPLICATION_ROOT}/doc", editor=False)
    base.init(app)
    admin.init(app)
    admin_settings.init(app)
