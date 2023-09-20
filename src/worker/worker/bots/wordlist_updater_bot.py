import requests

from .base_bot import BaseBot
from worker.log import logger


class WordlistUpdaterBot(BaseBot):
    type = "WORDLIST_UPDATER_BOT"
    name = "Wordlist Updater Bot"
    description = "Bot for updating word lists"

    def execute(self, word_list):
        url = word_list["link"]
        logger.info(f"Updating word list {word_list['name']} from {url}")
        response = requests.get(url=url)
        if not response.ok:
            logger.error(f"Failed to download word list {word_list['name']} - from {url} : {response.status_code}")
            return

        content_type = response.headers.get("content-type", "")
        if content_type == "text/csv" or url.endswith(".csv"):
            content_type = "text/csv"
            content = response.text
        elif content_type == "application/json" or url.endswith(".json"):
            content_type = "application/json"
            content = response.json()
        else:
            logger.error("Could not determine content type.")
            return

        logger.debug(f"Updating word list {word_list['name']} with {len(content)} entries - {content_type}")

        response = self.core_api.update_word_list(word_list["id"], content, content_type)

        if not response:
            logger.error(f"Failed to update word list {word_list['name']}")
            return

        logger.info(response)
        return response
