from os import path, chdir
import sys
from flask_sse import sse

chdir(path.dirname(path.abspath(__file__)))
sys.path.append(path.abspath('.'))
sys.path.append(path.abspath('../taranis-ng-common'))

from app import create_app

app = create_app()
app.register_blueprint(sse, url_prefix='/sse')
