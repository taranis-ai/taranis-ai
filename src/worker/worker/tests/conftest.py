import os
import sys
import pytest

current_path = os.getcwd()

if not current_path.endswith("src/worker"):
    sys.exit("Tests must be run from within src/worker")


@pytest.fixture(scope="session")
def celery_config():
    return {"broker_url": "memory://"}
