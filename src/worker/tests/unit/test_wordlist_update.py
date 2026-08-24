import pytest

from worker.config import Config
from worker.misc.wordlist_update import update_wordlist


def test_update_wordlist_rejects_empty_csv(requests_mock):
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/word-list/word-list-1",
        json={"name": "Empty list", "link": "https://wordlists.test/empty.csv"},
    )
    requests_mock.get("https://wordlists.test/empty.csv", text="", headers={"content-type": "text/csv"})

    with pytest.raises(ValueError, match="Downloaded CSV word list is empty"):
        update_wordlist("word-list-1")
