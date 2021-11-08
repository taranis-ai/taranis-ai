#! /usr/bin/env python

from flask_sse import sse

from app import create_app

app = create_app()
app.register_blueprint(sse, url_prefix='/sse')
