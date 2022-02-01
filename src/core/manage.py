#! /usr/bin/env python

from os import abort, getenv, read
import socket
import time
import logging
from flask import Flask

from managers import db_manager
from model import *
from remote.collectors_api import CollectorsApi

app = Flask(__name__)
app.config.from_object('config.Config')

if getenv("DEBUG").lower() == "true":
    app.logger.debug("Debug Mode: On")

db_manager.initialize(app)

# wait for the database to be ready
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((app.config.get('DB_URL'), 5432))
        s.close()
        break
    except socket.error as ex:
        time.sleep(0.1)

if __name__ == '__main__':
    # manager.run()
        with app.app_context():
            from scripts import permissions
            from scripts import sample_data

            data, count = user.User.get(None, None)
            if count:
                app.logger.error("Sample data already installed.")
                exit()

            app.logger.error("Installing sample data...")
            permissions.run(db_manager.db)
            sample_data.run(db_manager.db)
            app.logger.error("Sample data installed.")

