from datetime import datetime
from typing import Any, ClassVar, Literal

from models.base import TaranisBaseModel

class CollabParticipant(TaranisBaseModel):
    base_url: str
    role: Literal["owner", "participant"]
    joined_at: datetime | None

class CollabTextDocState(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    text: str
    version: int

class CollabTextSelectionPresence(TaranisBaseModel):
    snapshot_id: str
    field_name: Literal["title", "description", "summary", "comments"]
    session_id: str
    participant_base_url: str
    username: str
    anchor: int
    head: int

class CollabStorySnapshot(TaranisBaseModel):
    id: str
    title: str | None
    description: str | None
    created: datetime | None
    source_instance: str | None
    source_story_id: str | None
    persisted_local_story_id: str | None
    story: dict[str, Any]

class CollabWorkspaceChatMessage(TaranisBaseModel):
    id: str
    author: str
    text: str
    participant_base_url: str | None
    participant_short_name: str | None
    created_at: datetime | None

class CollabWorkspaceTask(TaranisBaseModel):
    id: str
    text: str
    owner: str | None
    participant_base_url: str | None
    participant_short_name: str | None
    status: Literal["todo", "doing", "done", "blocked"]
    due_label: str | None
    created_at: datetime | None

class CollabWorkspaceComment(TaranisBaseModel):
    id: str
    author: str
    text: str
    participant_base_url: str | None
    participant_short_name: str | None
    created_at: datetime | None

class CollabWorkspaceActivityItem(TaranisBaseModel):
    id: str
    text: str
    actor: str | None
    participant_base_url: str | None
    participant_short_name: str | None
    created_at: datetime | None

class CollabInvite(TaranisBaseModel):
    owner_base_url: str
    channel_id: str
    token: str
    join_url: str

class CollabChannelSummary(TaranisBaseModel):
    channel_id: str
    topic: str
    status: Literal["open", "closed"]
    owner_base_url: str
    story_count: int
    participant_count: int
    created_at: datetime | None
    updated_at: datetime | None
    invite: CollabInvite | None

class CollabChannelDetail(TaranisBaseModel):
    _core_endpoint: ClassVar[str]
    _model_name: ClassVar[str]
    _pretty_name: ClassVar[str]
    channel_id: str
    topic: str
    status: Literal["open", "closed"]
    owner_base_url: str
    active_instance_base_url: str | None
    invite: CollabInvite | None
    participants: list[CollabParticipant]
    presence: list[Any]
    locks: list[Any]
    shared_docs: list[CollabTextDocState]
    text_selections: list[CollabTextSelectionPresence]
    workspace: Any
    stories: list[CollabStorySnapshot]
    result_stories: list[CollabStorySnapshot]
    created_at: datetime | None
    updated_at: datetime | None
    is_owner: bool

class CollabChannelCreate(TaranisBaseModel):
    topic: str
    story_ids: list[str]

class CollabInviteRedeem(TaranisBaseModel):
    owner_base_url: str
    channel_id: str
    token: str

class CollabStoriesAdd(TaranisBaseModel):
    story_ids: list[str]

class CollabPeerJoin(TaranisBaseModel):
    token: str
    partner_base_url: str

class CollabPeerStoriesAdd(TaranisBaseModel):
    token: str
    partner_base_url: str
    stories: list[CollabStorySnapshot]

class CollabRemoteSync(TaranisBaseModel):
    token: str
    channel: CollabChannelDetail

class CollabFinalizeRequest(TaranisBaseModel):
    story_ids: list[str]

class CollabFinalizeResult(TaranisBaseModel):
    channel_id: str
    created_story_ids: list[str]
    report_story_ids: list[str]
