from typing import Literal

from models.base import TaranisBaseModel

type DiscussionKind = Literal["story", "report", "product"]
DISCUSSION_PERMISSIONS: dict[DiscussionKind, str]
COMMENT_MAX_LENGTH: int

class CommentPayload(TaranisBaseModel):
    body: str
