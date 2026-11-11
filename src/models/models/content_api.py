"""HTTP data shapes shared by assessment, analysis and worker operations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, field_validator, model_validator

from models import assess
from models.api import ErrorResponse, IdMessageResponse, MessageResponse
from models.base import TaranisBaseModel
from models.classification import Classification
from models.config_api import ListQuery
from models.types import TLPLevel


class Attribute(TaranisBaseModel):
    id: str | None = None
    key: str
    value: JsonValue = None


class Tag(TaranisBaseModel):
    model_config = ConfigDict(extra="allow", coerce_numbers_to_str=False)
    name: str = ""
    tag_type: str | None = None
    id: str | None = None
    news_item_id: str | None = None


TagPayload = list[str | Tag] | dict[str, str | Tag]
AttributePayload = list[str | Attribute] | dict[str, Attribute | JsonValue]


class AttributeEnvelope(BaseModel):
    attributes: AttributePayload


class NewsItemResponse(TaranisBaseModel):
    id: str
    osint_source_id: str | None
    title: str | None = None
    content: str | None = None
    author: str | None = None
    source: str | None = None
    link: str | None = None
    review: str | None = None
    language: str | None = None
    hash: str | None = None
    published: datetime | None = None
    collected: datetime | None = None
    updated: datetime | None = None
    story_id: str | None = None
    last_change: str | None = None
    attributes: list[Attribute] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    tlp_level: TLPLevel | None = None


class StoryResponse(TaranisBaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    summary: str | None = None
    comments: str | None = None
    important: bool | None = None
    read: bool | None = None
    likes: int | None = None
    dislikes: int | None = None
    relevance: int | None = None
    relevance_override: int | None = None
    revision: int | None = None
    last_change: str | None = None
    news_items: list[NewsItemResponse] = Field(default_factory=list)
    attributes: list[Attribute] | dict[str, Attribute] = Field(default_factory=list)
    tags: list[Tag] | dict[str, Tag] = Field(default_factory=list)
    tlp_level: TLPLevel | None = None
    misp_auto_update: assess.MispAutoUpdatePayload | None = None
    can_edit: bool = False
    bookmarked: bool = False


class StoryCounts(BaseModel):
    total_count: int
    read_count: int
    important_count: int
    in_reports_count: int
    biggest_story: int


class StoryPage(BaseModel):
    counts: StoryCounts | None = None
    items: list[StoryResponse]
    total_count: int | None = None


class ManualNewsInput(assess.NewsItem):
    osint_source_id: str = "manual"


class StoryInput(TaranisBaseModel):
    id: str | None = None
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    updated: datetime | None = None
    last_change: str | None = None
    news_items: list[ManualNewsInput] | list[str] | None = None
    important: bool | None = None
    read: bool | None = None
    summary: str | None = None
    comments: str | None = None
    relevance: int | None = None
    relevance_override: int | None = None
    tags: TagPayload | None = None
    attributes: AttributePayload | None = None
    conflict: bool = False
    news_items_to_delete: list[str] | None = None


class ContentQuery(ListQuery):
    range: str | None = None
    timefrom: datetime | None = None
    timeto: datetime | None = None
    read: bool | None = None
    important: bool | None = None
    relevant: bool | None = None
    in_analyze: bool | None = None
    in_report: bool | None = None
    completed: bool | None = None
    worker: bool | None = None
    story_id: str | None = None
    story_ids: list[str] | str = Field(default_factory=list)
    source: list[str] | str = Field(default_factory=list)
    group: list[str] | str = Field(default_factory=list)
    classification: Classification | None = None
    exclude_attr: str | None = None
    include_attr: str | None = None
    report_item_type_id: str | None = None
    no_count: bool = False

    @field_validator("read", "important", "relevant", "in_analyze", "in_report", "completed", "worker", "timefrom", "timeto", mode="before")
    @classmethod
    def empty_optional_filters(cls, value):
        return None if value == "" else value


class StoryFilters(assess.AssessSearchFilters):
    model_config = ConfigDict(extra="ignore")
    page: int = 0
    limit: int = 20
    offset: int | None = None
    no_count: bool = False
    exclude_attr: str | None = None


class StoryIds(BaseModel):
    story_ids: list[str]


class NewsIds(BaseModel):
    newsitem_ids: list[str]


class StoryGroups(BaseModel):
    story_ids: list[list[str]]


class BotAction(TaranisBaseModel):
    bot_id: str | None = None
    story_id: str | None = None
    story_ids: list[str] | str = Field(default_factory=list)
    report_id: str | None = None
    report_ids: list[str] | str = Field(default_factory=list)


class ContentError(ErrorResponse):
    id: str | None = None
    story_id: str | None = None
    story_ids: list[str] | None = None
    news_item_ids: list[str] | None = None
    skipped_news_item_story_id: str | None = None


class StoryAdded(MessageResponse):
    story_id: str
    news_item_ids: list[str]


class StoryUpdated(IdMessageResponse):
    story: StoryResponse


class NewsUpdated(MessageResponse):
    story_id: str
    news_item_id: str


class NewsDeleted(IdMessageResponse):
    story_id: str


class NewsBatch(MessageResponse):
    story_ids: list[str]
    news_item_ids: list[str]
    warning: str | None = None


class CollectionCounts(BaseModel):
    created: int
    updated: int
    grouped: int
    unchanged: int
    stale: int


class CollectionResult(NewsBatch):
    counts: CollectionCounts


class CollectionError(ErrorResponse):
    counts: CollectionCounts
    story_ids: list[str]
    news_item_ids: list[str]


class ConflictPair(BaseModel):
    local: StoryResponse
    new: StoryInput


class StoryConflictResponse(BaseModel):
    warning: str
    conflict: ConflictPair


class ConflictCount(BaseModel):
    conflicts_number: int


class NewsConflictError(BaseModel):
    error: ConflictCount


class MispDetails(BaseModel):
    story_ids: list[str]
    errors: list[ContentError | MessageResponse | StoryConflictResponse | NewsConflictError] = Field(default_factory=list)


class MispResult(MessageResponse):
    details: MispDetails


class MispError(ErrorResponse):
    details: MispDetails


class PartialTags(MessageResponse):
    errors: dict[str, str | int]


class LanguageUpdate(BaseModel):
    language: assess.BCP47 = None


class Revision(BaseModel):
    id: str
    revision: int
    created_at: datetime | None
    created_by: str | None
    created_by_id: str | None
    note: str | None


class RevisionData(Revision):
    # Historical snapshots retain the schema of the version that wrote them.
    data: dict[str, JsonValue]


class StoryRevisionPath(BaseModel):
    story_id: str
    revision_number: int


class ReportRevisionPath(BaseModel):
    report_item_id: str
    revision_number: int


class ReportLock(BaseModel):
    report_item_id: str
    locked: bool
    lock_time: datetime | None = None


class CountResponse(BaseModel):
    count: int


class BulkSuccess(BaseModel):
    story_id: str
    response: IdMessageResponse


class BulkResponse(MessageResponse):
    updated: int
    success: list[BulkSuccess]
    errors: list[ContentError]


class ReviewActionResponse(MessageResponse):
    story_id: str
    report_id: str | None


class ImportedStories(BaseModel):
    imported_stories: list[StoryResponse]


class ImportedNews(BaseModel):
    imported_news_items: list[NewsItemResponse]


class BookmarkWritten(IdMessageResponse):
    bookmark: assess.StoryBookmark


class BookmarkSaved(MessageResponse):
    bookmark: assess.StoryBookmark
    added_story_ids: list[str]


class BookmarkAdded(MessageResponse):
    added: int
    story_count: int


class BookmarkRemoved(MessageResponse):
    removed: int
    story_count: int


class NewsUpdate(TaranisBaseModel):
    title: str | None = None
    content: str | None = None
    author: str | None = None
    source: str | None = None
    link: str | None = None
    review: str | None = None
    language: assess.BCP47 = None
    published: datetime | None = None
    collected: datetime | None = None
    updated: datetime | None = None
    attributes: AttributePayload | None = None
    tags: TagPayload | None = None


class BulkWrite(BaseModel):
    story_ids: list[str] = Field(min_length=1)
    payload: assess.StoryUpdatePayload | None = None


class ContentImport(BaseModel):
    # Match the supported single, homogeneous-list and export-envelope formats.
    @model_validator(mode="before")
    @classmethod
    def validate_format(cls, value):
        envelope = isinstance(value, dict) and "items" in value
        rows = value["items"] if envelope else value
        rows = rows if isinstance(rows, list) else [rows]
        if not rows or not all(isinstance(row, dict) for row in rows):
            raise ValueError("Invalid JSON data for import.")
        kinds = {"story" if "news_items" in row else "news" for row in rows}
        if len(kinds) != 1:
            raise ValueError("Cannot mix story and news item imports.")
        adapter = TypeAdapter(list[StoryInput] if kinds == {"story"} else list[ManualNewsInput])
        adapter.validate_python(rows)
        return {"payload": value}

    payload: JsonValue


def validate_import(value):
    ContentImport.model_validate(value)
    return value


class Ungrouped(MessageResponse):
    new_stories_ids: list[str]
