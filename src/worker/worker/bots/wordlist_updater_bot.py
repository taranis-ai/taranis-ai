import csv
import requests

from .base_bot import BaseBot
from worker.log import logger


class WordlistUpdaterBot(BaseBot):
    type = "WORDLIST_UPDATER_BOT"
    name = "Wordlist Updater Bot"
    description = "Bot for updating word lists"

    def parse_csv(self, content) -> list:
        cr = csv.reader(content.splitlines(), delimiter=";", lineterminator="\n")
        headers = next(cr)
        return [dict(zip(headers, row)) for row in cr]

    def execute(self, word_list):
        url = word_list["link"]
        logger.info(f"Updating word list {word_list['name']} from {url}")
        response = requests.get(url=url)
        if not response.ok:
            logger.error(f"Failed to update word list {word_list['name']}")
            return
        content_type = response.headers["content-type"]
        entries = []
        if content_type == "text/csv" or url.endswith(".csv"):
            entries = self.parse_csv(response.content.decode("utf-8"))
        elif content_type == "application/json" or url.endswith(".json"):
            entries = response.json()
        else:
            logger.error(f"Unsupported content type {content_type}")
            return
        word_list["entries"] = entries

        self.core_api.update_word_list(word_list)
        logger.info(f"Word list {word_list['name']} updated")
        return f"Word list {word_list['name']} updated"
