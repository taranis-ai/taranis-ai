import os
import pytest
import re
import json

from worker.config import Config


@pytest.fixture(scope="session")
def stories():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    story_json = os.path.join(dir_path, "test_stories.json")
    with open(story_json) as f:
        yield json.load(f)


@pytest.fixture(autouse=True)
def set_transformers_offline(requests_mock):
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    requests_mock.real_http = True


@pytest.fixture
def story_get_mock(requests_mock, stories):
    yield requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories", json=stories)


@pytest.fixture
def tags_update_mock(requests_mock):
    yield requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/tags", json={"message": "Sucessfully updated story"})


@pytest.fixture
def ner_bot_mock(requests_mock):
    print(f"Mocking: {Config.NLP_API_ENDPOINT}/")
    yield requests_mock.post(
        f"{Config.NLP_API_ENDPOINT}/",
        json=[
            {"entity": "B-PER", "index": 3, "score": 0.9992660880088806, "word": "John"},
            {"entity": "B-LOC", "index": 7, "score": 0.9996646642684937, "word": "Amsterdam"},
            {"entity": "B-LOC", "index": 7, "score": 0.9996286630630492, "word": "Paris"},
        ],
    )


@pytest.fixture
def news_item_attribute_update_mock(requests_mock):
    def match_callback(request, context):
        news_item_id = request.url.split("/")[6]
        return {"message": f"Successfully updated attributes oif news item with id: '{news_item_id}'"}

    yield requests_mock.put(re.compile(rf"{Config.TARANIS_CORE_URL}/bots/news-item/.+/attributes"), json=match_callback)


@pytest.fixture
def story_attribute_update_mock(requests_mock):
    def match_callback(request, context):
        story_id = request.url.split("/")[6]
        return {"message": f"Successfully updated attributes oif news item with id: '{story_id}'"}

    yield requests_mock.patch(re.compile(rf"{Config.TARANIS_CORE_URL}/bots/story/.+/attributes"), json=match_callback)


@pytest.fixture
def cybersec_classifier_mock(requests_mock):
    print(f"Mocking: {Config.CYBERSEC_CLASSIFIER_API_ENDPOINT}/")
    yield requests_mock
