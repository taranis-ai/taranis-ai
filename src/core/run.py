#! /usr/bin/env python

from flask_sse import sse

from gevent import monkey
monkey.patch_all()

from app import create_app

app = create_app()
app.register_blueprint(sse, url_prefix='/sse')
