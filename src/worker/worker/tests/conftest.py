import json
import os
import sys

import pytest


current_path = os.getcwd()

if not current_path.endswith("src/worker"):
    sys.exit("Tests must be run from within src/worker")


@pytest.fixture(scope="session")
def redis_config():
    """Redis configuration for testing with fakeredis."""
    return {"host": "localhost", "port": 6379}


@pytest.fixture(scope="session")
def stories():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    story_json = os.path.join(dir_path, "story_list.json")
    with open(story_json) as f:
        yield json.load(f)
