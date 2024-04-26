#!/usr/bin/env python

import os
import multiprocessing
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
Granian("core", interface=Interfaces.WSGI, address=address, port=port, log_level=loglevel, workers=workers).serve(target_loader=app_loader)
