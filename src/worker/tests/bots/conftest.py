import json
import os

import pytest

from worker.config import Config


@pytest.fixture(scope="session")
def stories():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    story_json = os.path.join(dir_path, "test_stories.json")
    with open(story_json) as f:
        yield json.load(f)


@pytest.fixture
def story_get_mock(requests_mock, stories):
    yield requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=stories)
