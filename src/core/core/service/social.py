import base64
from datetime import timedelta
from io import BytesIO

from models.assess import NewsItem as NewsItemData
from models.social import AttachPosts, BeatFilters, CollectedImage, Contribution, FigureSelection
from models.types import COLLECTOR_TYPES, TLPLevel
from PIL import Image, ImageOps
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import selectinload

from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.osint_source import OSINTSource
from core.model.social import SocialImage, SocialPost
from core.model.story import Story
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


SOCIAL_TYPES = {COLLECTOR_TYPES.MASTODON_COLLECTOR: "mastodon", COLLECTOR_TYPES.REDDIT_COLLECTOR: "reddit"}


def visible_sources(user, write=False):
    query = select(OSINTSource).where(OSINTSource.type.in_(SOCIAL_TYPES))
    query = RoleBasedAccessService.filter_query_with_acl(query, RBACQuery(user, "osint_source", require_write_access=write))
    levels = user.get_highest_tlp().get_accessible_levels()
    return {s.id: s for s in db.session.scalars(query.order_by(OSINTSource.name)) if s.tlp_level.value in levels}


def store_image(image: SocialImage, incoming: CollectedImage):
    if not incoming.data:
        return
    raw = base64.b64decode(incoming.data, validate=True)
    if image.original == raw:
        return
    try:
        with Image.open(BytesIO(raw), formats=("JPEG", "PNG", "WEBP")) as photo:
            if not photo.format or photo.width * photo.height > 40_000_000 or getattr(photo, "is_animated", False):
                return
            mime = Image.MIME[photo.format]
            photo.thumbnail((360, 240))
            preview = ImageOps.exif_transpose(photo).convert("RGB")
            buffer = BytesIO()
            preview.save(buffer, "JPEG", quality=85)
    except (ValueError, OSError, Image.DecompressionBombError):
        return
    image.mime, image.original, image.thumbnail = mime, raw, buffer.getvalue()


def ingest(source, data: Contribution):
    post = db.session.scalar(select(SocialPost).filter_by(source_id=source.id, key=data.key).with_for_update())
    if post is None:
        post = SocialPost(source=source, key=data.key, platform=SOCIAL_TYPES[source.type])
        db.session.add(post)
    values = data.model_dump(exclude={"images", "published", "url"})
    values.update(published=NewsItemData.normalize_datetime(data.published), url=str(data.url))
    for field, value in values.items():
        setattr(post, field, value)
    post.checked = SocialPost.utcnow()
    if len({i.key for i in data.images}) != len(data.images):
        raise ValueError("Duplicate image")
    previous = {i.key: i for i in post.images}
    for position, incoming in enumerate(data.images):
        image = previous.pop(incoming.key, None)
        if image is None:
            image = SocialImage(key=incoming.key, position=position, alt=incoming.alt)
            post.images.append(image)
        image.position, image.alt = position, incoming.alt
        store_image(image, incoming)
    for image in previous.values():
        post.images.remove(image)
    db.session.commit()
    return {"id": post.id}


def due_keys(source):
    cutoff = SocialPost.utcnow() - timedelta(hours=6)
    stmt = select(SocialPost.key).where(SocialPost.source_id == source.id, SocialPost.checked < cutoff)
    return list(db.session.scalars(stmt.order_by(SocialPost.checked, SocialPost.id).limit(100)))


def post_view(post, user):
    item = post.item
    story = item.story if item else None
    return {
        **post.to_dict(exclude={"item_id", "checked"}),
        "story_id": story.id if story and story.allowed_to_read(user) else None,
        "images": [{"id": i.id, "alt": i.alt, "available": bool(i.mime)} for i in post.images],
    }


def feed(user, sources, filters: BeatFilters, page):
    source_ids = sources.keys() if not filters.sources else set(filters.sources).intersection(sources)
    base = select(SocialPost.source_id, SocialPost.thread).where(SocialPost.source_id.in_(source_ids))
    if filters.platform:
        base = base.where(SocialPost.platform == filters.platform)
    if filters.search:
        term = filters.search.strip()
        base = base.where(or_(*(field.icontains(term, autoescape=True) for field in (SocialPost.title, SocialPost.body, SocialPost.author))))
    if filters.images:
        base = base.where(SocialPost.images.any())
    matches = base.distinct().subquery()
    groups = (
        select(
            SocialPost.source_id,
            SocialPost.thread,
            func.max(SocialPost.activity).label("latest"),
            func.sum(case((SocialPost.key != SocialPost.thread, 1), else_=0)).label("replies"),
        )
        .join(matches, and_(SocialPost.source_id == matches.c.source_id, SocialPost.thread == matches.c.thread))
        .group_by(SocialPost.source_id, SocialPost.thread)
        .order_by(func.max(SocialPost.activity).desc(), SocialPost.source_id, SocialPost.thread)
        .offset(page * 30)
        .limit(31)
        .subquery()
    )
    # A collected reply may outlive its parent. Use the oldest visible member as the row in that case.
    root = (
        select(SocialPost.id)
        .where(SocialPost.source_id == groups.c.source_id, SocialPost.thread == groups.c.thread)
        .order_by((SocialPost.key == SocialPost.thread).desc(), SocialPost.published, SocialPost.id)
        .limit(1)
        .correlate(groups)
        .scalar_subquery()
    )
    query = (
        select(SocialPost, groups.c.replies, groups.c.latest)
        .select_from(groups)
        .join(SocialPost, SocialPost.id == root)
        .options(selectinload(SocialPost.images), selectinload(SocialPost.item))
        .order_by(groups.c.latest.desc(), groups.c.source_id, groups.c.thread)
    )
    rows = [
        {**post_view(p, user), "replies": replies, "latest": SocialPost.serialize_datetime(latest)}
        for p, replies, latest in db.session.execute(query)
    ]
    return {"rows": rows[:30], "more": len(rows) > 30}


def thread_view(post, user, page):
    stmt = select(SocialPost).filter_by(source_id=post.source_id, thread=post.thread).options(selectinload(SocialPost.images))
    posts = list(
        db.session.scalars(
            stmt.order_by((SocialPost.key == post.thread).desc(), SocialPost.published, SocialPost.id).offset(50 * page).limit(51)
        )
    )
    parents = {
        p.key: p
        for p in db.session.scalars(
            select(SocialPost).where(SocialPost.source_id == post.source_id, SocialPost.key.in_({p.parent for p in posts if p.parent}))
        )
    }
    return {
        "posts": [
            {
                **post_view(p, user),
                "context": (parents[p.parent].warning or parents[p.parent].body or parents[p.parent].title) if p.parent in parents else None,
            }
            for p in posts[:50]
        ],
        "more": len(posts) > 50,
    }


def attach(data: AttachPosts, user):
    ids = list(dict.fromkeys(data.posts))
    sources = visible_sources(user, write=True)
    posts = list(
        db.session.scalars(
            select(SocialPost).where(SocialPost.id.in_(ids), SocialPost.source_id.in_(sources)).order_by(SocialPost.id).with_for_update()
        )
    )
    if len(posts) != len(ids):
        return {"error": "Selected contribution unavailable"}, 404
    existing = {p.item.story_id for p in posts if p.item}
    if data.story_id:
        story = db.session.scalar(select(Story).filter_by(id=data.story_id).with_for_update())
        if not story or not story.allowed_to_read(user):
            return {"error": "Story unavailable"}, 404
        if not story.allowed_to_update(user):
            return {"error": "Story is read-only"}, 403
    else:
        if "ASSESS_CREATE" not in user.get_permissions():
            return {"error": "Story creation unavailable"}, 403
        if existing:
            if len(existing) == 1 and all(p.item for p in posts):
                story = Story.get(next(iter(existing)))
                if story and story.title == data.title.strip() and story.allowed_to_read(user):
                    return {"id": story.id}, 200
            return {"error": "Selection already belongs to a Story"}, 409
        story = Story(title=data.title.strip())
        db.session.add(story)
    if existing - {story.id}:
        return {"error": "Selection already belongs to another Story"}, 409
    if all(p.item for p in posts):
        return {"id": story.id}, 200
    actor = Story.last_change_for_user(user)
    with db.session.no_autoflush:
        for p in sorted(posts, key=lambda p: ids.index(p.id)):
            if p.item:
                continue
            item = NewsItem(
                title=f"{p.platform.title()} contribution",
                source="Social monitor",
                osint_source_id=p.source_id,
                hash=NewsItem.get_hash(content=p.id),
                published=p.published,
                collected=p.activity,
                attributes=[{"key": "TLP", "value": p.source.tlp_level.value}],
            )
            story.news_items.append(item)
            p.item = item
    db.session.flush()
    story.clear_bot_execution_attributes()
    story.read = False
    story.update_status(change=actor)
    story.record_revision(user=user, note="Attached social contributions")
    db.session.commit()
    return {"id": story.id}, 200


def eligible(image):
    post = image.post
    return bool(
        image.mime
        and post.source.tlp_level == TLPLevel.CLEAR
        and post.item
        and post.item.story
        and post.item.story.tlp_level == TLPLevel.CLEAR
    )


def report_images(report, user=None, *, selected_only=False):
    """Resolve image references through current Story membership and, for analysts, source access."""
    query = select(SocialImage).join(SocialPost).join(NewsItem, SocialPost.item_id == NewsItem.id)
    if selected_only:
        if not report.figure_selection:
            return {}
        query = query.where(SocialImage.id.in_([figure["image_id"] for figure in report.figure_selection]))
    stories = report.stories
    if user is not None:
        query = query.where(SocialPost.source_id.in_(visible_sources(user)))
        stories = [story for story in stories if story.allowed_to_read(user)]
    query = query.where(NewsItem.story_id.in_([story.id for story in stories])).order_by(
        SocialPost.published, SocialPost.id, SocialImage.position
    )
    return {image.id: image for image in db.session.scalars(query)}


def has_restricted_figures(report, user):
    selected = report_images(report, selected_only=True)
    return bool(selected and selected.keys() - report_images(report, user, selected_only=True).keys())


def save_figures(report, data: FigureSelection, user):
    images = report_images(report, user)
    allowed = {image.id for image in images.values() if eligible(image)}
    selected = [figure.image_id for figure in data.figures]
    if len(set(selected)) != len(selected) or set(selected) - allowed:
        return {"error": "Selected figure unavailable for publication"}, 400
    if report_images(report, selected_only=True).keys() - images.keys():
        return {"error": "Report contains restricted figures"}, 403
    report.figure_selection = [figure.model_dump() for figure in data.figures]
    db.session.commit()
    return {"message": "Report figures saved"}, 200


def render_figures(report):
    images = report_images(report, selected_only=True)
    out = []
    for figure in report.figure_selection:
        image = images.get(figure["image_id"])
        if not image or not eligible(image) or not image.original:
            continue
        post = image.post
        out.append(
            {
                "image_id": image.id,
                "caption": figure["caption"],
                "alt": figure["alt"] or image.alt,
                "credit": f"{post.author or 'Unknown author'} · {post.platform.title()}",
                "url": post.url,
                "src": f"data:{image.mime};base64,{base64.b64encode(image.original).decode('ascii')}",
            }
        )
    return out
