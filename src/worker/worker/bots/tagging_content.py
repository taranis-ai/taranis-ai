def _news_item_content_for_tagging(news_item: dict, separator: str = " ") -> str:
    return separator.join(str(news_item.get(field) or "") for field in ("title", "review", "content"))
