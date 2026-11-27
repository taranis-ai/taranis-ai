from typing import Annotated, Literal

from pydantic import ConfigDict, StringConstraints

from models.base import TaranisBaseModel


DiscussionKind = Literal["story", "report", "product"]
DISCUSSION_PERMISSIONS: dict[DiscussionKind, str] = {"story": "ASSESS_ACCESS", "report": "ANALYZE_ACCESS", "product": "PUBLISH_ACCESS"}
COMMENT_MAX_LENGTH = 10000


class CommentPayload(TaranisBaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=COMMENT_MAX_LENGTH, pattern=r"^[^\x00]*$")]
