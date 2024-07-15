#!/usr/bin/env python

import os
import multiprocessing
import sentry_sdk
from granian import Granian
from granian.constants import Interfaces
from granian.log import LogLevels

from core import create_app

loglevel = LogLevels.info
if os.getenv("DEBUG", "false").lower() == "true":
    loglevel = LogLevels.debug

workers = int(os.getenv("GRANIAN_WORKERS", multiprocessing.cpu_count()))
address = os.getenv("GRANIAN_ADDRESS", "0.0.0.0")
port = int(os.getenv("GRANIAN_PORT", 8080))


def app_loader(target):
    if target != "core":
        raise RuntimeError("Should never get there")
    return create_app(initial_setup=False)


create_app(initial_setup=True)
sentry_sdk.init(
dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

Granian("core", interface=Interfaces.WSGI, address=address, port=port, log_level=loglevel, workers=workers).serve(target_loader=app_loader)
