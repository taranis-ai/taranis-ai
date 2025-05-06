import pytest
import json
import os

from worker.config import Config


def file_loader(filename, base_path: str | None = None):
    """
    Load a file from the specified filename and base path.

    :param filename: The name of the file to load.
    :param base_path: Optional base path to load the file from.
                    If not provided, defaults to the directory of the test file.
    :return: The content of the file as a string.
    :raises OSError: If the file cannot be read.
    """
    try:
        if base_path:
            file_path = os.path.join(base_path, filename)
        else:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            file_path = os.path.join(dir_path, filename)

        with open(file_path, "r") as f:
            return f.read()
    except OSError as e:
        raise OSError(f"Error while reading file: {e}") from e


@pytest.fixture
def news_item_template():
    template_base_path = "worker/connectors/definitions/objects/taranis-news-item"
    template_content = file_loader("definition.json", base_path=template_base_path)
    return json.loads(template_content)


@pytest.fixture
def story_template():
    template_base_path = "worker/connectors/definitions/objects/taranis-story"
    template_content = file_loader("definition.json", base_path=template_base_path)
    return json.loads(template_content)


@pytest.fixture
def story_get_by_id_mock(requests_mock, stories):
    # stories_json = json.dumps(stories[10])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories?story_id=11", json=[stories[10]])
