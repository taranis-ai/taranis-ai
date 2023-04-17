import requests

from .base_bot import BaseBot
from shared.schema import word_list
from bots.managers.log_manager import logger


class WordlistUpdaterBot(BaseBot):
    type = "WORDLIST_UPDATER_BOT"
    name = "Wordlist Updater Bot"
    description = "Bot for updating word lists"

    def execute(self):
        def load_file(source, word_list_format):
            if "http" in source and word_list_format == "txt":
                response = requests.get(source)
                content = response.text.strip().split("\r\n")
                content = [word for word in content]
            else:
                with open(source) as file:
                    content = [line.rstrip() for line in file]

            return content

        try:
            data_url = self.parameters["DATA_URL"]
            data_format = self.parameters["FORMAT"]
            word_list_id = self.parameters["WORD_LIST_ID"]
            word_list_category_name = self.parameters["WORD_LIST_CATEGORY"]
            delete_word_entries = self.parameters["DELETE"].lower()

            source_word_list = load_file(data_url, data_format)

            categories = self.core_api.get_categories(word_list_id)

            if not any(category["name"] == word_list_category_name for category in categories):
                name = word_list_category_name
                description = "Stop word list category created by Updater Bot."
                entries = []

                category = word_list.WordListCategory(name, description, "", entries)
                word_list_category_schema = word_list.WordListCategorySchema()

                self.core_api.add_word_list_category(word_list_id, word_list_category_schema.dump(category))

            if delete_word_entries == "yes":
                self.core_api.delete_word_list_category_entries(word_list_id, word_list_category_name)

            entries = []

            for word in source_word_list:
                value = word
                description = ""

                entry = word_list.WordListEntry(value, description)
                entries.append(entry)

            word_list_entries_schema = word_list.WordListEntrySchema(many=True)
            self.core_api.update_word_list_category_entries(
                word_list_id,
                word_list_category_name,
                word_list_entries_schema.dump(entries),
            )

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            data_url_preset = self.parameters["DATA_URL"]
            format_preset = self.parameters["FORMAT"]
            logger.log_debug(data_url_preset + format_preset)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
