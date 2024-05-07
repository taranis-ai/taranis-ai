import subprocess
import time
import pytest
import requests


@pytest.fixture(scope="session")
def headers():
    return {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcxNDY3NTMzNywianRpIjoiZTA3NjRiZmQtMDUzOC00NDg4LTljZmMtY2NkZmFjZGM2MGU2IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6ImFkbWluIiwibmJmIjoxNzE0Njc1MzM3LCJjc3JmIjoiZWRmOTc2NTktNzAxMy00NzViLTg3ZDUtNTM0NTczM2VmY2NlIiwidXNlcl9jbGFpbXMiOnsiaWQiOjEsIm5hbWUiOiJBcnRodXIgRGVudCIsInJvbGVzIjpbMV19fQ.siZID18vdHC1tyQnW8B9KuwqU-B2QJZHPBpknAyB-qg"
    }


@pytest.fixture(scope="session")
def start_core():
    subprocess.Popen(["flask", "run"])


@pytest.fixture(scope="session")
def start_gui(start_core):
    subprocess.Popen(["npm", "run", "build"], cwd="../gui")
    subprocess.Popen(["python", "-m", "http.server", "8081"], cwd="../gui/dist")


@pytest.fixture(scope="session")
def feed_source(start_gui, headers):
    source_data = {
        "id": "99",
        "description": "This is a test source",
        "name": "Test Source",
        "parameters": [{"FEED_URL": "https://url/feed.xml"}],
        "type": "rss_collector",
    }

    url = "http://localhost:5000/api/config/osint-sources"

    response = requests.post(url, json=source_data, headers=headers)
    if response.status_code != 201:
        pytest.fail(f"Failed to create feed source: {response.text}")

    return source_data["id"]


@pytest.fixture(scope="session")
def news_items(feed_source, headers):
    news_item_1 = {
        "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
        "content": "TEST CONTENT YYYY",
        "source": "https://www.some.link/RSSNewsfeed.xml",
        "title": "Mobile World Congress 2023",
        "author": "",
        "collected": "2022-02-21T15:00:14.086285",
        "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
        "review": "",
        "link": "https://www.some.other.link/2023.html",
        "osint_source_id": feed_source,
        "published": "2022-02-21T15:01:14.086285",
    }
    news_item_2 = {
        "id": "0a129597-592d-45cb-9a80-3218108b29a0",
        "content": "TEST CONTENT XXXX",
        "source": "https://www.content.xxxx.link/RSSNewsfeed.xml",
        "title": "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen",
        "author": "",
        "collected": "2023-01-20T15:00:14.086285",
        "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da6",
        "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
        "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
        "osint_source_id": feed_source,
        "published": "2023-01-20T19:15:00+01:00",
    }

    requests.post("http://localhost:5000/api/assess/news-items", json=news_item_1, headers=headers)
    requests.post("http://localhost:5000/api/assess/news-items", json=news_item_2, headers=headers)
