#! /usr/bin/env python

import os
from dotenv import load_dotenv

from gevent import monkey
monkey.patch_all()

from app import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
