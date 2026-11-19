from typing import Any

from models.discussion import DISCUSSION_PERMISSIONS, DiscussionKind
from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import InstrumentedAttribute, joinedload
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.model.comment import Comment
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User


PARENTS: dict[DiscussionKind, tuple[type[Story] | type[ReportItem] | type[Product], InstrumentedAttribute[str | None]]] = {
    "story": (Story, Comment.story_id),
    "report": (ReportItem, Comment.report_item_id),
    "product": (Product, Comment.product_id),
}


def visible_parents(kind: DiscussionKind, user: User) -> Select:
    if kind == "story":
        return Story.visible_query(user)
    if kind == "report":
        return ReportItem.visible_query(user)
    return Product.get_filter_query_with_acl({}, user)


def can_delete_parent(parent: Story | ReportItem | Product, user: User) -> bool:
    permissions = user.get_permissions()
    if isinstance(parent, Story):
        return (
            "ASSESS_DELETE" in permissions
            and not Story.is_assigned_to_report([parent.id])
            and all(item.allowed_with_acl(user, require_write_access=True) for item in parent.news_items)
        )
    if isinstance(parent, ReportItem):
        return "ANALYZE_DELETE" in permissions and parent.access_allowed(user, require_write_access=True)
    return (
        "PUBLISH_DELETE" in permissions
        and parent.product_type is not None
        and parent.product_type.allowed_with_acl(user, require_write_access=True)
    )


def recent_discussions(user: User, kind: DiscussionKind | None, page: int, limit: int) -> dict[str, Any]:
    queries = []
    for parent_kind, (parent, parent_key) in PARENTS.items():
        if (kind is not None and kind != parent_kind) or DISCUSSION_PERMISSIONS[parent_kind] not in user.get_permissions():
            continue
        # One index lookup per visible parent yields its latest comment.
        latest_id = (
            select(Comment.id)
            .where(parent_key == parent.id)
            .order_by(Comment.created_at.desc().nulls_last(), Comment.id.desc())
            .limit(1)
            .correlate(parent)
            .scalar_subquery()
        )
        queries.append(
            visible_parents(parent_kind, user)
            .with_only_columns(parent.id.label("parent_id"), parent.title, literal(parent_kind).label("kind"), Comment.id.label("comment_id"))
            .join(Comment, Comment.id == latest_id)
        )
    if not queries:
        return {"items": [], "has_more": False}

    discussions = union_all(*queries).subquery()
    query = (
        select(Comment, discussions.c.kind, discussions.c.parent_id, discussions.c.title)
        .join(discussions, discussions.c.comment_id == Comment.id)
        .options(joinedload(Comment.author))
        .order_by(Comment.created_at.desc().nulls_last(), Comment.id.desc())
        .offset((page - 1) * limit)
        .limit(limit + 1)
    )
    rows = db.session.execute(query).all()
    return {
        "items": [
            {
                "kind": kind,
                "parent_id": parent_id,
                "title": title,
                "author": comment.author.name if comment.author else None,
                "created_at": Comment.serialize_datetime(comment.created_at) if comment.created_at else None,
                "excerpt": " ".join(comment.body.split())[:180],
            }
            for comment, kind, parent_id, title in rows[:limit]
        ],
        "has_more": len(rows) > limit,
    }


def comment_page(
    parent: Story | ReportItem | Product,
    parent_key: InstrumentedAttribute[str | None],
    user: User,
    page: int,
    limit: int,
) -> dict[str, Any]:
    can_moderate = can_delete_parent(parent, user)
    query = select(Comment).where(parent_key == parent.id)
    total_count = db.session.scalar(select(func.count(Comment.id)).where(parent_key == parent.id)) or 0
    items = db.session.scalars(
        query.options(joinedload(Comment.author))
        .order_by(Comment.created_at.desc().nulls_last(), Comment.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "parent": {"id": parent.id, "title": parent.title},
        "items": [
            {
                "id": comment.id,
                "body": comment.body,
                "author": comment.author.name if comment.author else None,
                "created_at": Comment.serialize_datetime(comment.created_at) if comment.created_at else None,
                "edited_at": Comment.serialize_datetime(comment.edited_at) if comment.edited_at else None,
                "can_edit": comment.author_id == user.id,
                "can_delete": can_moderate or comment.author_id == user.id,
            }
            for comment in reversed(items)
        ],
        "total_count": total_count,
    }
