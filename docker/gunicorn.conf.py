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
wsgi_app = os.getenv("APP_MODULE", "run:app")
use_reload = False
post_worker_init = "core.post_worker_init"
on_starting = "core.on_starting_and_exit"
on_exit = "core.on_starting_and_exit"


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


class CustomGunicornLogger(glogging.Logger):
    def setup(self, cfg):
        super().setup(cfg)

        # Add filters to Gunicorn logger
        logger = logging.getLogger("gunicorn.access")
        logger.addFilter(HealthCheckFilter())


class HealthCheckFilter(logging.Filter):
    def filter(self, record):
        return "GET /api/v1/isalive" not in record.getMessage()


accesslog = "-"
logger_class = CustomGunicornLogger
