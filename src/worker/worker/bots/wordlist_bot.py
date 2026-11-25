import re
from collections import deque
from typing import Any

from worker.log import logger

from .base_bot import BaseBot
from .tagging_content import _news_item_content_for_tagging


def _fold_for_shortlist(text: str) -> str:
    # re.IGNORECASE groups I, i, İ and ı together. Plain casefold() splits that group.
    return text.replace("İ", "i").replace("ı", "i").casefold()


class _AhoCorasickMatcher:
    """Single-pass multi-pattern matcher used to shortlist dictionary entries."""

    def __init__(self, patterns: list[str], *, ignore_case: bool) -> None:
        self._ignore_case = ignore_case
        self._next: list[dict[str, int]] = [{}]
        self._fail: list[int] = [0]
        self._outputs: list[list[str]] = [[]]
        self._empty_patterns: list[str] = []

        deduped: dict[str, list[str]] = {}
        for pattern in patterns:
            if not pattern:
                self._empty_patterns.append(pattern)
                continue
            key = _fold_for_shortlist(pattern) if ignore_case else pattern
            deduped.setdefault(key, []).append(pattern)

        for key, originals in deduped.items():
            state = 0
            for ch in key:
                nxt = self._next[state].get(ch)
                if nxt is None:
                    nxt = len(self._next)
                    self._next[state][ch] = nxt
                    self._next.append({})
                    self._fail.append(0)
                    self._outputs.append([])
                state = nxt
            self._outputs[state].extend(originals)

        queue: deque[int] = deque()
        for nxt in self._next[0].values():
            queue.append(nxt)

        while queue:
            state = queue.popleft()
            for ch, nxt in self._next[state].items():
                queue.append(nxt)
                fail = self._fail[state]
                while fail and ch not in self._next[fail]:
                    fail = self._fail[fail]
                self._fail[nxt] = self._next[fail].get(ch, 0)
                if self._outputs[self._fail[nxt]]:
                    self._outputs[nxt].extend(self._outputs[self._fail[nxt]])

    def shortlist(self, text: str) -> set[str]:
        """Return candidate original patterns that appear in *text*."""
        candidates = set(self._empty_patterns)
        haystack = _fold_for_shortlist(text) if self._ignore_case else text
        state = 0
        for ch in haystack:
            while state and ch not in self._next[state]:
                state = self._fail[state]
            state = self._next[state].get(ch, 0)
            if self._outputs[state]:
                candidates.update(self._outputs[state])
        return candidates


class WordlistBot(BaseBot):
    def __init__(self):
        super().__init__()

        self.type = "WORDLIST_BOT"
        self.name = "Wordlist Bot"
        self.description = "Bot for tagging news items by wordlist"

    def execute(self, parameters: dict | None = None) -> dict[str, Any]:
        if not parameters:
            parameters = {}
        ignore_case = self._set_ignore_case_flag(parameters)
        override_existing_tags = parameters.get("OVERRIDE_EXISTING_TAGS", True)

        word_list_entries = self._get_word_list_entries()
        if not word_list_entries:
            return {"message": "No word list entries found"}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        found_tags = self._find_tags_for_stories(data, word_list_entries, override_existing_tags, ignore_case)
        logger.info({"message": f"{len(found_tags)} tags found, saving bot type to story attributes..."})
        return found_tags

    @staticmethod
    def _set_ignore_case_flag(parameters):
        return re.IGNORECASE if parameters.get("IGNORECASE", True) else re.NOFLAG

    def _get_word_list_entries(self):
        if word_lists := self.core_api.get_words_for_tagging_bot():
            return [entry for word_list in word_lists["items"] for entry in word_list["entries"]]
        return None

    @staticmethod
    def _prepare_matcher(
        word_list_entries: list[dict[str, str]],
        ignore_case: re.RegexFlag | int,
    ) -> tuple[dict[str, str], _AhoCorasickMatcher]:
        entry_set = {item["value"]: item["category"] for item in word_list_entries}
        matcher = _AhoCorasickMatcher(list(entry_set), ignore_case=bool(ignore_case & re.IGNORECASE))
        return entry_set, matcher

    def _find_tags_for_stories(self, data, word_list_entries, override_existing_tags, ignore_case) -> dict[str, dict[str, str]]:
        prepared = self._prepare_matcher(word_list_entries, ignore_case)
        found_tags = {}
        for story in data:
            for news_item in story["news_items"]:
                found_tags[news_item["id"]] = self._find_tags(
                    news_item,
                    word_list_entries,
                    override_existing_tags,
                    ignore_case,
                    prepared=prepared,
                )
                self.save_tags(news_item["id"], news_item.get("story_id", story["id"]), found_tags[news_item["id"]])
        return found_tags

    def _find_tags(
        self,
        news_item,
        word_list_entries,
        override_existing_tags,
        ignore_case,
        *,
        prepared: tuple[dict[str, str], _AhoCorasickMatcher] | None = None,
    ) -> dict[str, str]:
        findings = {}
        entry_set, matcher = prepared or self._prepare_matcher(word_list_entries, ignore_case)
        existing_tags = self._tag_names(news_item.get("tags") or {})

        all_content = _news_item_content_for_tagging(news_item)
        candidates = matcher.shortlist(all_content)

        for entry, category in entry_set.items():
            if entry not in candidates:
                continue
            if re.search(r"\b" + re.escape(entry) + r"\b", all_content, ignore_case):
                if entry in existing_tags and not override_existing_tags:
                    continue
                findings[entry] = category

        return findings

    @staticmethod
    def _tag_names(tags) -> set[str]:
        if isinstance(tags, dict):
            return set(tags)
        if isinstance(tags, list):
            return {tag["name"] for tag in tags if isinstance(tag, dict) and isinstance(tag.get("name"), str)}
        return set()
