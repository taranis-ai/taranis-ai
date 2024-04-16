#! /usr/bin/env python

from core import create_app

if __name__ == "__main__":
    app = create_app(initial_setup=True)
    app.run()
