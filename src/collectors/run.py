#! /usr/bin/env python

# patch things
from gevent import monkey
monkey.patch_all()

import os

from gevent import monkey
monkey.patch_all()

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
