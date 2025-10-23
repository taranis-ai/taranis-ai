import uuid
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING
from sqlalchemy import or_, func
from sqlalchemy.orm import aliased, Mapped, relationship
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.sql.expression import false, null, true
from sqlalchemy.sql import Select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.exc import IntegrityError
from collections import Counter

from core.managers.history_meta import VersionedRelation
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger
from core.model.user import User
from core.model.role import TLPLevel
from core.model.news_item_tag import NewsItemTag
from core.model.role_based_access import ItemType
from core.model.osint_source import OSINTSourceGroup, OSINTSource, OSINTSourceGroupOSINTSource
from core.model.news_item import NewsItem

# from core.model.news_item_attribute import NewsItemAttribute
from core.service.role_based_access import RBACQuery, RoleBasedAccessService
from core.model.story_conflict import StoryConflict
from core.model.news_item_conflict import NewsItemConflict


class StoryNewsItemAttribute(VersionedRelation, BaseModel):
    __tablename__ = "story_news_item_attribute"

    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(
        db.String(64), db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True
    )
    created: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)
    removed: Mapped[datetime] = db.Column(db.DateTime)

    story: Mapped["Story"] = relationship("Story", back_populates="story_attribute_links")
    attribute: Mapped["NewsItemAttribute"] = relationship("NewsItemAttribute", back_populates="story_attribute_links")
