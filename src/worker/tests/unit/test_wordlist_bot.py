import re

from worker.bots.wordlist_bot import WordlistBot


def _make_bot(saved: list[tuple[str, str, dict[str, str]]]) -> WordlistBot:
    bot = WordlistBot.__new__(WordlistBot)
    bot.save_tags = lambda news_item_id, story_id, tags: saved.append((news_item_id, story_id, tags))
    return bot


def test_wordlist_bot_matches_multiword_overlapping_unicode_and_preserves_last_category_wins():
    saved: list[tuple[str, str, dict[str, str]]] = []
    bot = _make_bot(saved)

    entries = [
        {"value": "Exchange", "category": "old_cat"},
        {"value": "Exchange", "category": "product"},
        {"value": "Exchange Server", "category": "platform"},
        {"value": "Intel", "category": "vendor"},
        {"value": "İstanbul", "category": "city"},
        {"value": "Straße", "category": "unicode"},
        {"value": "ExistingTag", "category": "new_cat"},
    ]
    data = [
        {
            "id": "story-1",
            "news_items": [
                {
                    "id": "item-1",
                    "story_id": "story-1",
                    "title": "Microsoft EXCHANGE SERVER on ıntel",
                    "review": "STRASSE in Istanbul",
                    "content": "ExistingTag stays if override is false",
                    "tags": {"ExistingTag": "keep"},
                }
            ],
        }
    ]

    found = bot._find_tags_for_stories(data, entries, override_existing_tags=False, ignore_case=re.IGNORECASE)
    assert found["item-1"] == {
        "Exchange": "product",
        "Exchange Server": "platform",
        "Intel": "vendor",
        "İstanbul": "city",
    }
    assert saved == [("item-1", "story-1", found["item-1"])]


def test_wordlist_bot_respects_case_sensitive_mode():
    saved: list[tuple[str, str, dict[str, str]]] = []
    bot = _make_bot(saved)

    entries = [
        {"value": "ExactCase", "category": "cat"},
        {"value": "lower", "category": "cat"},
    ]
    data = [
        {
            "id": "story-2",
            "news_items": [
                {
                    "id": "item-2",
                    "story_id": "story-2",
                    "title": "exactcase and lower",
                    "review": "",
                    "content": "",
                    "tags": {},
                }
            ],
        }
    ]

    found = bot._find_tags_for_stories(data, entries, override_existing_tags=True, ignore_case=re.NOFLAG)
    assert found["item-2"] == {"lower": "cat"}
