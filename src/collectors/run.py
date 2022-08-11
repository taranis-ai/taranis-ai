#! /usr/bin/env python

from app import create_app
from gevent import monkey

monkey.patch_all()

app = create_app()

if __name__ == "__main__":
    app.run()
