#! /usr/bin/env python

import socket
import time
from flask import Flask
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from managers import db_manager
from model import *

app = Flask(__name__)
app.config.from_object('config.Config')

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

migrate = Migrate(app=app, db=db_manager.db)

manager = Manager(app=app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
