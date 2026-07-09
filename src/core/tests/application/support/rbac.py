import uuid
from unittest.mock import Mock

from core.managers.db_manager import db
from core.model.role import TLPLevel


def admin_ops_user(tlp_level: TLPLevel = TLPLevel.CLEAR):
    user = Mock()
    user.get_permissions.return_value = ["ADMIN_OPERATIONS"]
    user.get_highest_tlp.return_value = tlp_level
    return user


def create_rbac_source_story(label: str):
    from core.model.news_item import NewsItem
    from core.model.osint_source import OSINTSource
    from core.model.story import Story

    source = OSINTSource(
        id=str(uuid.uuid4()),
        name=f"RBAC {label} Source",
        description="RBAC test source",
        type="rss_collector",
        parameters={"FEED_URL": f"https://example.invalid/{label}.xml"},
    )
    db.session.add(source)
    db.session.flush()

    story_payload = {
        "title": f"RBAC {label} Story",
        "news_items": [
            {
                "id": str(uuid.uuid4()),
                "title": f"RBAC {label} News",
                "content": f"RBAC {label} Content",
                "source": "unit-test",
                "link": f"https://example.invalid/{label}",
                "osint_source_id": source.id,
                "hash": NewsItem.get_hash(title=f"RBAC {label} News", link=f"https://example.invalid/{label}"),
                "collected": "2025-01-01T00:00:00",
                "published": "2025-01-01T00:00:00",
            }
        ],
    }
    result, status = Story.add(story_payload)
    assert status == 200
    story = Story.get(result["story_id"])
    assert story is not None
    assert story.news_items
    return source, story, story.news_items[0]


def create_rbac_source_group(name: str, sources):
    from core.model.osint_source import OSINTSourceGroup

    group = OSINTSourceGroup(
        id=str(uuid.uuid4()),
        name=name,
        description="RBAC test source group",
    )
    group.osint_sources = list(sources)
    db.session.add(group)
    db.session.commit()
    return group


def grant_acl(role, item_type, item_id: str, read_only: bool = True):
    from core.model.role_based_access import RoleBasedAccess

    acl = RoleBasedAccess(
        id=str(uuid.uuid4()),
        name=f"RBAC Test ACL {uuid.uuid4().hex}",
        description="RBAC test ACL",
        item_type=item_type,
        item_id=item_id,
        roles=[role.id],
        read_only=read_only,
        enabled=True,
    )
    db.session.add(acl)
    db.session.commit()
    return acl


def create_rbac_report_item(label: str, tlp_level: TLPLevel | None = None):
    from core.model.report_item import ReportItem, ReportItemAttribute
    from core.model.report_item_type import ReportItemType

    report_type = ReportItemType.get_by_title("OSINT Report")
    assert report_type is not None

    report_item, status = ReportItem.add(
        {
            "id": str(uuid.uuid4()),
            "title": f"RBAC {label} Report",
            "completed": False,
            "report_item_type_id": report_type.id,
        },
        None,
    )
    assert status == 200
    assert isinstance(report_item, ReportItem)

    if tlp_level and (tlp_attribute := ReportItemAttribute.find_attribute_by_title(report_item.id, "TLP")):
        report_item.update_attributes({str(tlp_attribute.id): tlp_level.value}, True)

    return report_item


def visible_story_ids(story_ids: list[str], user) -> set[str]:
    from core.model.story import Story

    payload, status = Story.get_by_filter_json({"story_ids": story_ids, "no_count": True}, user)
    assert status == 200
    return {item["id"] for item in payload["items"]}
