import json
import os
import sys
from unittest.mock import Mock

import niquests
import pytest
import requests_mock.adapter as requests_mock_adapter
import requests_mock.mocker as requests_mock_mocker
import requests_mock.request as requests_mock_request
import requests_mock.response as requests_mock_response
from niquests.packages import urllib3


sys.modules["requests"] = niquests
sys.modules["requests.adapters"] = niquests.adapters
sys.modules["requests.exceptions"] = niquests.exceptions
sys.modules["requests.packages.urllib3"] = urllib3

requests_mock_mocker.requests = niquests
requests_mock_adapter.BaseAdapter = niquests.adapters.BaseAdapter
requests_mock_adapter.requote_uri = niquests.utils.requote_uri
requests_mock_request.requests = niquests
requests_mock_response.HTTPAdapter = niquests.adapters.HTTPAdapter
requests_mock_response.RequestsCookieJar = niquests.cookies.RequestsCookieJar
requests_mock_response.MockRequest = niquests.cookies.MockRequest
requests_mock_response.MockResponse = niquests.cookies.MockResponse
requests_mock_response.merge_cookies = niquests.cookies.merge_cookies
requests_mock_response.cookiejar_from_dict = niquests.cookies.cookiejar_from_dict
requests_mock_response.get_encoding_from_headers = niquests.utils.get_encoding_from_headers
requests_mock_response._http_adapter = niquests.adapters.HTTPAdapter()


current_path = os.getcwd()

if not current_path.endswith("src/worker"):
    sys.exit("Tests must be run from within src/worker")


class FakeQueue:
    enqueued_calls: list[dict[str, object]] = []

    def __init__(self, name, connection=None):
        self.name = name
        self.connection = connection

    def enqueue(self, task, *args, job_id=None, **kwargs):
        type(self).enqueued_calls.append(
            {
                "task": task,
                "args": args,
                "job_id": job_id,
                "kwargs": kwargs,
            }
        )
        return object()


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


@pytest.fixture
def mock_job():
    job = Mock()
    job.id = "test-job-123"
    return job


@pytest.fixture
def fake_queue():
    FakeQueue.enqueued_calls = []
    yield FakeQueue
    FakeQueue.enqueued_calls = []
