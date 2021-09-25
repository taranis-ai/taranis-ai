#! /usr/bin/python3

import sys, os
from dotenv import load_dotenv, find_dotenv

sys.path.insert(0,os.getcwd())

load_dotenv(find_dotenv())
# expected keys:
# DB_URL
# DB_DATABASE
# DB_USER
# DB_PASSWORD
# JWT_SECRET_KEY

from app import create_app
application = create_app()

