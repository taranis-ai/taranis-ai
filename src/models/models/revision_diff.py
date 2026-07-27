from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from pydantic import Field, field_validator

from models.base import TaranisBaseModel


class RevisionDiffSegment(TaranisBaseModel):
    text: str
    highlighted: bool = False


class RevisionDiffRevision(TaranisBaseModel):
    id: str
    revision: int
    created_at: str | None = None
    created_by: str | None = None
    created_by_id: str | None = None
    note: str | None = None

    @field_validator("id", "created_by_id", mode="before")
    @classmethod
    def coerce_ids(cls, value: Any) -> Any:
        return str(value) if value is not None else None


class RevisionDiffResource(TaranisBaseModel):
    id: str
    title: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: Any) -> Any:
        return str(value) if value is not None else None


class RevisionDiffChange(TaranisBaseModel):
    field: str
    group: str | None = None
    old_value: Any | None = None
    new_value: Any | None = None
    old_segments: list[RevisionDiffSegment] = Field(default_factory=list)
    new_segments: list[RevisionDiffSegment] = Field(default_factory=list)


class RevisionDiff(TaranisBaseModel):
    resource: RevisionDiffResource
    from_revision: RevisionDiffRevision
    to_revision: RevisionDiffRevision
    changes: list[RevisionDiffChange] = Field(default_factory=list)


def _build_inline_segments(old_text: str, new_text: str) -> tuple[list[RevisionDiffSegment], list[RevisionDiffSegment]]:
    old_segments: list[RevisionDiffSegment] = []
    new_segments: list[RevisionDiffSegment] = []

    matcher = SequenceMatcher(a=old_text, b=new_text)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_piece = old_text[i1:i2]
        new_piece = new_text[j1:j2]

        if tag == "equal":
            if old_piece:
                old_segments.append(RevisionDiffSegment(text=old_piece))
            if new_piece:
                new_segments.append(RevisionDiffSegment(text=new_piece))
            continue

        if tag in {"delete", "replace"} and old_piece:
            old_segments.append(RevisionDiffSegment(text=old_piece, highlighted=True))

        if tag in {"insert", "replace"} and new_piece:
            new_segments.append(RevisionDiffSegment(text=new_piece, highlighted=True))

    return old_segments, new_segments


def _append_change(changes: list[RevisionDiffChange], field: str, old_value: Any, new_value: Any, group: str | None = None) -> None:
    if old_value == new_value:
        return

    change = RevisionDiffChange(field=field, group=group, old_value=old_value, new_value=new_value)
    if isinstance(old_value, str) and isinstance(new_value, str):
        old_segments, new_segments = _build_inline_segments(old_value, new_value)
        if old_segments or new_segments:
            change.old_segments = old_segments
            change.new_segments = new_segments

    changes.append(change)


def _format_joined_titles(titles: list[str], limit: int | None = None) -> str:
    if limit is not None and len(titles) > limit:
        return ", ".join(titles[:limit]) + f" and {len(titles) - limit} more"
    return ", ".join(titles)


def _normalized_tag_names(data: dict[str, Any]) -> set[str]:
    tag_names = set()
    for tag in data.get("tags") or []:
        if not isinstance(tag, dict):
            continue
        name = tag.get("name")
        if not isinstance(name, str):
            continue
        normalized_name = name.strip()
        if normalized_name:
            tag_names.add(normalized_name)
    return tag_names


def _attribute_values_by_key(data: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for attr in data.get("attributes", []):
        if not isinstance(attr, dict):
            continue
        key = attr.get("key")
        if isinstance(key, str) and key:
            values[key] = attr.get("value")
    return values


def _story_title_map(stories: list[dict[str, Any]]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for story in stories:
        story_id = story.get("id")
        if isinstance(story_id, str) and story_id:
            titles[story_id] = story.get("title") or story_id
    return titles


def _resolve_story_value(value: Any, story_map: dict[str, str]) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value

    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) == 1:
        part = parts[0]
        return story_map.get(part, part)
    return ", ".join(story_map.get(part, part) for part in parts)


def _build_revision_diff(
    resource_id: str,
    resource_title: str | None,
    from_revision: dict[str, Any],
    to_revision: dict[str, Any],
    changes: list[RevisionDiffChange],
) -> RevisionDiff:
    return RevisionDiff(
        resource=RevisionDiffResource(id=resource_id, title=resource_title),
        from_revision=RevisionDiffRevision(**{key: value for key, value in from_revision.items() if key != "data"}),
        to_revision=RevisionDiffRevision(**{key: value for key, value in to_revision.items() if key != "data"}),
        changes=changes,
    )


def build_story_revision_diff_payload(
    story_id: str,
    story_title: str | None,
    from_revision: dict[str, Any],
    to_revision: dict[str, Any],
) -> RevisionDiff:
    from_data = from_revision.get("data") or {}
    to_data = to_revision.get("data") or {}
    changes: list[RevisionDiffChange] = []

    _append_change(changes, "Title", from_data.get("title"), to_data.get("title"))
    _append_change(changes, "Description", from_data.get("description"), to_data.get("description"))
    _append_change(changes, "Summary", from_data.get("summary"), to_data.get("summary"))
    _append_change(changes, "Comments", from_data.get("comments"), to_data.get("comments"))
    _append_change(changes, "Likes", from_data.get("likes", 0), to_data.get("likes", 0))
    _append_change(changes, "Dislikes", from_data.get("dislikes", 0), to_data.get("dislikes", 0))

    from_tags = _normalized_tag_names(from_data)
    to_tags = _normalized_tag_names(to_data)

    added_tags = sorted(to_tags - from_tags)
    removed_tags = sorted(from_tags - to_tags)

    if added_tags:
        changes.append(RevisionDiffChange(field="Tags Added", old_value=None, new_value=_format_joined_titles(added_tags)))

    if removed_tags:
        changes.append(RevisionDiffChange(field="Tags Removed", old_value=_format_joined_titles(removed_tags), new_value=None))

    from_news_items = [item for item in from_data.get("news_items", []) if isinstance(item, dict)]
    to_news_items = [item for item in to_data.get("news_items", []) if isinstance(item, dict)]
    from_news_ids = {item.get("id") for item in from_news_items}
    to_news_ids = {item.get("id") for item in to_news_items}

    added_items = to_news_ids - from_news_ids
    removed_items = from_news_ids - to_news_ids

    if added_items:
        item_titles = [item.get("title") or item.get("id") for item in to_news_items if item.get("id") in added_items]
        changes.append(
            RevisionDiffChange(
                field="News Items Added",
                old_value=None,
                new_value=_format_joined_titles([title for title in item_titles if isinstance(title, str)], limit=5),
            )
        )

    if removed_items:
        item_titles = [item.get("title") or item.get("id") for item in from_news_items if item.get("id") in removed_items]
        changes.append(
            RevisionDiffChange(
                field="News Items Removed",
                old_value=_format_joined_titles([title for title in item_titles if isinstance(title, str)], limit=5),
                new_value=None,
            )
        )

    from_attrs = _attribute_values_by_key(from_data)
    to_attrs = _attribute_values_by_key(to_data)

    for key in sorted(set(from_attrs) | set(to_attrs)):
        _append_change(changes, key, from_attrs.get(key), to_attrs.get(key))

    return _build_revision_diff(story_id, story_title, from_revision, to_revision, changes)


def build_report_revision_diff_payload(
    report_item_id: str,
    report_title: str | None,
    from_revision: dict[str, Any],
    to_revision: dict[str, Any],
) -> RevisionDiff:
    from_data = from_revision.get("data") or {}
    to_data = to_revision.get("data") or {}
    changes: list[RevisionDiffChange] = []

    _append_change(changes, "Title", from_data.get("title"), to_data.get("title"))
    _append_change(changes, "Completed", from_data.get("completed"), to_data.get("completed"))

    story_map = _story_title_map(
        [story for story in from_data.get("stories", []) if isinstance(story, dict)]
        + [story for story in to_data.get("stories", []) if isinstance(story, dict)]
    )

    from_groups = from_data.get("grouped_attributes", []) or []
    to_groups = to_data.get("grouped_attributes", []) or []

    from_attributes: dict[tuple[str, str], Any] = {}
    from_attribute_types: dict[tuple[str, str], Any] = {}
    for group in from_groups:
        if not isinstance(group, dict):
            continue
        group_title = group.get("title") or ""
        for attribute in group.get("attributes", []) or []:
            if not isinstance(attribute, dict):
                continue
            key = (group_title, attribute.get("title") or "")
            from_attributes[key] = attribute.get("value")
            from_attribute_types[key] = attribute.get("type")

    to_attributes: dict[tuple[str, str], Any] = {}
    to_attribute_types: dict[tuple[str, str], Any] = {}
    for group in to_groups:
        if not isinstance(group, dict):
            continue
        group_title = group.get("title") or ""
        for attribute in group.get("attributes", []) or []:
            if not isinstance(attribute, dict):
                continue
            key = (group_title, attribute.get("title") or "")
            to_attributes[key] = attribute.get("value")
            to_attribute_types[key] = attribute.get("type")

    for group_title, attribute_title in sorted(set(from_attributes) | set(to_attributes)):
        from_value = from_attributes.get((group_title, attribute_title))
        to_value = to_attributes.get((group_title, attribute_title))
        if from_value == to_value:
            continue

        attribute_type = from_attribute_types.get((group_title, attribute_title)) or to_attribute_types.get((group_title, attribute_title))
        if attribute_type == "STORY":
            from_value = _resolve_story_value(from_value, story_map)
            to_value = _resolve_story_value(to_value, story_map)

        changes.append(RevisionDiffChange(field=attribute_title, group=group_title or None, old_value=from_value, new_value=to_value))

    from_story_ids = {story.get("id") for story in from_data.get("stories", []) if isinstance(story, dict)}
    to_story_ids = {story.get("id") for story in to_data.get("stories", []) if isinstance(story, dict)}

    added_story_ids = to_story_ids - from_story_ids
    removed_story_ids = from_story_ids - to_story_ids

    if added_story_ids:
        story_titles = [
            story.get("title") or story.get("id")
            for story in to_data.get("stories", [])
            if isinstance(story, dict) and story.get("id") in added_story_ids
        ]
        changes.append(
            RevisionDiffChange(
                field="Stories Added", old_value=None, new_value=", ".join(title for title in story_titles if isinstance(title, str))
            )
        )

    if removed_story_ids:
        story_titles = [
            story.get("title") or story.get("id")
            for story in from_data.get("stories", [])
            if isinstance(story, dict) and story.get("id") in removed_story_ids
        ]
        changes.append(
            RevisionDiffChange(
                field="Stories Removed", old_value=", ".join(title for title in story_titles if isinstance(title, str)), new_value=None
            )
        )

    return _build_revision_diff(report_item_id, report_title, from_revision, to_revision, changes)
