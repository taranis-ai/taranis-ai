import json
import multiprocessing
import os
import logging
from gunicorn import glogging

workers_per_core = int(os.getenv("WORKERS_PER_CORE", "2"))
default_web_concurrency = int(workers_per_core * multiprocessing.cpu_count())
web_concurrency = os.getenv("WEB_CONCURRENCY", default_web_concurrency)
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "80")
bind = os.getenv("BIND", f"{host}:{port}")
use_loglevel = os.getenv("LOG_LEVEL", "info")
use_reload = False

if os.getenv("DEBUG", "false").lower() == "true":
    use_loglevel = "debug"
    use_reload = True


# Gunicorn config variables
loglevel = use_loglevel
workers = web_concurrency
reload = use_reload
keepalive = 120
timeout = 600
errorlog = "-"
accesslog = "-"
log_file = "-"
disable_redirect_access_to_syslog = True

# For debugging and testing
log_data = {
    "loglevel": loglevel,
    "workers": workers,
    "bind": bind,
    # Additional, non-gunicorn variables
    "workers_per_core": workers_per_core,
    "host": host,
    "port": port,
}
print(json.dumps(log_data))

class CustomGunicornLogger(glogging.Logger):

    def setup(self, cfg):
        super().setup(cfg)

        # Add filters to Gunicorn logger
        logger = logging.getLogger("gunicorn.access")
        logger.addFilter(HealthCheckFilter())

class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return 'GET /api/v1/isalive' not in record.getMessage()

accesslog = '-'
logger_class = CustomGunicornLogger

