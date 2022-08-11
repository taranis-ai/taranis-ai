#! /usr/bin/env python

from app import create_app
from gevent import monkey
from flask_sse import sse
from psycogreen import gevent as g


monkey.patch_all()
g.patch_psycopg()

app = create_app()
app.register_blueprint(sse, url_prefix="/sse")

if __name__ == "__main__":
    app.run()
