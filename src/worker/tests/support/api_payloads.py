"""Core collection envelopes used by collector workflow fixtures."""


def collection_result(*, message="", story_ids=None, news_item_ids=None, counts=None, **extra):
    return {
        "message": message,
        "story_ids": story_ids or [],
        "news_item_ids": news_item_ids or [],
        "counts": counts or {"created": 0, "updated": 0, "grouped": 0, "unchanged": 0, "stale": 0},
        **extra,
    }
