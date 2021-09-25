import os
from dotenv import load_dotenv
from os import path, chdir
import sys

chdir(path.dirname(path.abspath(__file__)))
sys.path.append(path.abspath('.'))
sys.path.append(path.abspath('../taranis-ng-common'))

from app import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(port=os.getenv('FLASK_RUN_PORT'))
