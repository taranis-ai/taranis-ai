import re
from .base_bot import BaseBot
from worker.log import logger


class WordlistBot(BaseBot):
    TYPE = "WORDLIST_BOT"
    NAME = "Wordlist Bot"
    DESCRIPTION = "Bot for tagging news items by wordlist"

    def execute(self, parameters=None):
        if not parameters:
            return

        try:
            filter_dict = self.get_filter_dict(parameters)
            ignore_case = self._set_ignore_case_flag(parameters)
            override_existing_tags = parameters.get("OVERRIDE_EXISTING_TAGS", True)

            word_list_entries = self._get_word_list_entries()
            if not word_list_entries:
                return "No word lists found"

            data = self.core_api.get_news_items_aggregate(filter_dict=filter_dict)
            if not data:
                return "No data found"

            found_tags = self._find_tags_for_aggregates(data, word_list_entries, override_existing_tags, ignore_case)
            logger.debug(found_tags)
            self.core_api.update_tags(found_tags)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.TYPE}")
            return str(error)

    @staticmethod
    def _set_ignore_case_flag(parameters):
        return re.IGNORECASE if parameters.get("IGNORECASE", "false").lower() == "true" else re.NOFLAG

    def _get_word_list_entries(self):
        if word_lists := self.core_api.get_words_for_tagging_bot():
            return [entry for word_list in word_lists["items"] for entry in word_list["entries"]]
        return

    def _find_tags_for_aggregates(self, data, word_list_entries, override_existing_tags, ignore_case):
        found_tags = {}
        logger.info(f"Extracting tags from news items: {len(data)}")
        for i, aggregate in enumerate(data):
            if i % max(len(data) // 10, 1) == 0:
                logger.debug(f"Extracting words from {aggregate['id']}: {i}/{len(data)}")
            if findings := self._find_tags(aggregate, word_list_entries, override_existing_tags, ignore_case):
                found_tags[aggregate["id"]] = findings
        return found_tags

    def _find_tags(self, aggregate, word_list_entries, override_existing_tags, ignore_case):
        findings = {}
        entry_set = {item["value"]: item["category"] for item in word_list_entries}
        existing_tags = aggregate["tags"] or {}

        all_content = self._aggregate_content(aggregate)

        for entry, category in entry_set.items():
            if re.search(r"\b" + re.escape(entry) + r"\b", all_content, ignore_case):
                if entry in existing_tags and not override_existing_tags:
                    continue
                findings[entry] = {"tag_type": category}

        return findings

    @staticmethod
    def _aggregate_content(aggregate):
        return " ".join(
            [
                news_item["news_item_data"]["title"] + news_item["news_item_data"]["review"] + news_item["news_item_data"]["content"]
                for news_item in aggregate["news_items"]
            ]
        )
