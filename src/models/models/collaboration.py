from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import Field

from models.base import TaranisBaseModel


class CollabParticipant(TaranisBaseModel):
    base_url: str
    role: Literal["owner", "participant"] = "participant"
    joined_at: datetime | None = None


class CollabFieldLock(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    participant_base_url: str
    session_id: str
    username: str
    acquired_at: datetime | None = None
    expires_at: datetime | None = None


class CollabPresence(TaranisBaseModel):
    session_id: str
    participant_base_url: str
    username: str
    connected_at: datetime | None = None
    last_seen_at: datetime | None = None
    selected_story_id: str | None = None


class CollabTextDocState(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    text: str = ""
    version: int = 0


class CollabTextDocChange(TaranisBaseModel):
    from_pos: int = Field(alias="from")
    to: int
    insert: str = ""

    model_config = {"populate_by_name": True}


class CollabTextDocHistoryEntry(TaranisBaseModel):
    version: int
    op_id: str
    session_id: str
    changes: list[CollabTextDocChange] = Field(default_factory=list)


class CollabTextDocRuntime(CollabTextDocState):
    history: list[CollabTextDocHistoryEntry] = Field(default_factory=list)


class CollabTextSelectionPresence(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    session_id: str
    participant_base_url: str
    username: str
    anchor: int = 0
    head: int = 0


class CollabWorkspaceDecision(TaranisBaseModel):
    id: str
    text: str
    owner: str | None = None
    status: Literal["open", "done"] = "open"
    created_at: datetime | None = None


class CollabWorkspaceTask(TaranisBaseModel):
    id: str
    text: str
    owner: str | None = None
    participant_base_url: str | None = None
    participant_short_name: str | None = None
    status: Literal["todo", "doing", "done", "blocked"] = "todo"
    due_label: str | None = None
    created_at: datetime | None = None


class CollabWorkspaceComment(TaranisBaseModel):
    id: str
    author: str
    text: str
    participant_base_url: str | None = None
    participant_short_name: str | None = None
    created_at: datetime | None = None


class CollabWorkspaceChatMessage(TaranisBaseModel):
    id: str
    author: str
    text: str
    participant_base_url: str | None = None
    participant_short_name: str | None = None
    created_at: datetime | None = None


class CollabWorkspaceTimelineEvent(TaranisBaseModel):
    id: str
    title: str
    note: str | None = None
    time_label: str | None = None
    created_at: datetime | None = None


class CollabWorkspaceActivityItem(TaranisBaseModel):
    id: str
    text: str
    actor: str | None = None
    participant_base_url: str | None = None
    participant_short_name: str | None = None
    created_at: datetime | None = None


class CollabWorkspaceBriefing(TaranisBaseModel):
    impact: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)
    related_story_ids: list[str] = Field(default_factory=list)
    source_labels: list[str] = Field(default_factory=list)


class CollabWorkspaceState(TaranisBaseModel):
    focused_story_id: str | None = None
    active_mode: Literal["story", "briefing"] = "story"
    briefing: CollabWorkspaceBriefing = Field(default_factory=CollabWorkspaceBriefing)
    decisions: list[CollabWorkspaceDecision] = Field(default_factory=list)
    tasks: list[CollabWorkspaceTask] = Field(default_factory=list)
    comments: list[CollabWorkspaceComment] = Field(default_factory=list)
    chat_messages: list[CollabWorkspaceChatMessage] = Field(default_factory=list)
    timeline_events: list[CollabWorkspaceTimelineEvent] = Field(default_factory=list)
    activity_items: list[CollabWorkspaceActivityItem] = Field(default_factory=list)


class CollabRuntimeChannel(TaranisBaseModel):
    presence: list[CollabPresence] = Field(default_factory=list)
    locks: list[CollabFieldLock] = Field(default_factory=list)
    shared_docs: list[CollabTextDocRuntime] = Field(default_factory=list)
    text_selections: list[CollabTextSelectionPresence] = Field(default_factory=list)


class CollabStorySnapshot(TaranisBaseModel):
    id: str
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    source_instance: str | None = None
    source_story_id: str | None = None
    persisted_local_story_id: str | None = None
    story: dict[str, Any] = Field(default_factory=dict)


class CollabInvite(TaranisBaseModel):
    owner_base_url: str
    channel_id: str
    token: str
    join_url: str


class CollabChannelSummary(TaranisBaseModel):
    channel_id: str
    topic: str
    status: Literal["open", "closed"] = "open"
    owner_base_url: str
    story_count: int = 0
    participant_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    invite: CollabInvite | None = None


class CollabChannelDetail(TaranisBaseModel):
    _core_endpoint: ClassVar[str] = "/assess/collab/channels"
    _model_name: ClassVar[str] = "collab_channel"
    _pretty_name: ClassVar[str] = "Collaboration"

    channel_id: str
    topic: str
    status: Literal["open", "closed"] = "open"
    owner_base_url: str
    active_instance_base_url: str | None = None
    invite: CollabInvite | None = None
    participants: list[CollabParticipant] = Field(default_factory=list)
    presence: list[CollabPresence] = Field(default_factory=list)
    locks: list[CollabFieldLock] = Field(default_factory=list)
    shared_docs: list[CollabTextDocState] = Field(default_factory=list)
    text_selections: list[CollabTextSelectionPresence] = Field(default_factory=list)
    workspace: CollabWorkspaceState = Field(default_factory=CollabWorkspaceState)
    stories: list[CollabStorySnapshot] = Field(default_factory=list)
    result_stories: list[CollabStorySnapshot] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_owner: bool = False


class CollabChannelCreate(TaranisBaseModel):
    topic: str
    story_ids: list[str] = Field(default_factory=list)


class CollabInviteRedeem(TaranisBaseModel):
    owner_base_url: str
    channel_id: str
    token: str


class CollabStoriesAdd(TaranisBaseModel):
    story_ids: list[str] = Field(default_factory=list)


class CollabPeerJoin(TaranisBaseModel):
    token: str
    partner_base_url: str


class CollabPeerStoriesAdd(TaranisBaseModel):
    token: str
    partner_base_url: str
    stories: list[CollabStorySnapshot] = Field(default_factory=list)


class CollabStoryUpdatePayload(TaranisBaseModel):
    title: str | None = None
    description: str | None = None
    summary: str | None = None
    comments: str | None = None


class CollabLiveActor(TaranisBaseModel):
    base_url: str
    session_id: str
    username: str


class CollabLiveLockRequest(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    actor: CollabLiveActor
    selected_story_id: str | None = None


class CollabLivePresenceRequest(TaranisBaseModel):
    actor: CollabLiveActor
    selected_story_id: str | None = None


class CollabLiveStoryPatch(TaranisBaseModel):
    snapshot_id: str
    payload: CollabStoryUpdatePayload = Field(default_factory=CollabStoryUpdatePayload)
    actor: CollabLiveActor


class CollabLiveStoryOpChange(TaranisBaseModel):
    from_pos: int = Field(alias="from")
    to: int
    insert: str = ""

    model_config = {"populate_by_name": True}


class CollabLiveStoryOpsSubmit(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    version: int = 0
    op_id: str
    updates: list[CollabLiveStoryOpChange] = Field(default_factory=list)
    actor: CollabLiveActor


class CollabLiveSelectionUpdate(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    anchor: int
    head: int
    actor: CollabLiveActor


class CollabLiveSelectionClear(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    actor: CollabLiveActor


class CollabLiveMoveNewsItem(TaranisBaseModel):
    source_snapshot_id: str
    target_snapshot_id: str
    news_item_id: str
    actor: CollabLiveActor


class CollabLiveWorkspacePatch(TaranisBaseModel):
    target: Literal["workspace", "briefing", "decision", "task", "comment", "chat_message", "timeline_event", "activity_item"]
    action: Literal["set", "upsert", "remove"]
    actor: CollabLiveActor
    item_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class CollabPeerRealtimeEnvelope(TaranisBaseModel):
    token: str
    partner_base_url: str
    message: dict[str, Any] = Field(default_factory=dict)


class CollabRealtimeMessage(TaranisBaseModel):
    type: str
    channel_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CollabStoryUpdate(TaranisBaseModel):
    snapshot_id: str
    payload: CollabStoryUpdatePayload = Field(default_factory=CollabStoryUpdatePayload)


class CollabPeerStoryUpdate(TaranisBaseModel):
    token: str
    partner_base_url: str
    snapshot_id: str
    payload: CollabStoryUpdatePayload = Field(default_factory=CollabStoryUpdatePayload)


class CollabMoveNewsItem(TaranisBaseModel):
    source_snapshot_id: str
    target_snapshot_id: str
    news_item_id: str


class CollabPeerMoveNewsItem(TaranisBaseModel):
    token: str
    partner_base_url: str
    source_snapshot_id: str
    target_snapshot_id: str
    news_item_id: str


class CollabRemoteSync(TaranisBaseModel):
    token: str
    channel: CollabChannelDetail


class CollabFinalizeRequest(TaranisBaseModel):
    story_ids: list[str] = Field(default_factory=list)


class CollabFinalizeResult(TaranisBaseModel):
    channel_id: str
    persisted_story_ids: list[str] = Field(default_factory=list)
    created_story_ids: list[str] = Field(default_factory=list)
    updated_story_ids: list[str] = Field(default_factory=list)
    report_story_ids: list[str] = Field(default_factory=list)
