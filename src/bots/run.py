#! /usr/bin/env python

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
