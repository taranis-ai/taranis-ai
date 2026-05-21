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


class CollabLiveMoveNewsItem(TaranisBaseModel):
    source_snapshot_id: str
    target_snapshot_id: str
    news_item_id: str
    actor: CollabLiveActor


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
