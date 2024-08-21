from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship

from typing import Any, TYPE_CHECKING
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger


if TYPE_CHECKING:
    from core.model.story import Story


class StoryLink(BaseModel):
    __tablename__ = "story_links"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    story_id: Mapped[str] = db.Column(db.ForeignKey("story.id"))
    links: Mapped[str] = db.Column(db.String(255))
    story: Mapped["Story"] = relationship("Story", back_populates="links")

    def __init__(self, links, story_id):
        self.story_id = story_id
        self.links = links
