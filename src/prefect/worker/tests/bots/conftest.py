import os
import pytest

from worker.config import Config


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
