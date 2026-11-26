from uuid import UUID

import pytest

from core.managers.db_manager import db
from core.model.comment import Comment
from core.model.news_item_attribute import NewsItemAttribute
from core.model.permission import Permission
from core.model.product import Product
from core.model.product_type import ProductType
from core.model.role import Role, TLPLevel
from core.model.role_based_access import ItemType
from core.model.story import Story
from core.model.user import User
from tests.application.support.rbac import create_rbac_report_item, create_rbac_source_story, grant_acl


ROOT = "/api/discussions"


@pytest.mark.parametrize("kind", ["story", "report", "product"])
def test_comment_crud_and_parent_cascade(client, session, auth_header, auth_header_user_permissions, kind):
    role = Role.filter_by_name("User")
    role.permissions.extend(
        permission for permission in Permission.get_bulk(["ANALYZE_ACCESS", "PUBLISH_ACCESS"]) if permission not in role.permissions
    )
    if kind == "story":
        source, parent, _ = create_rbac_source_story("discussion")
        item_type, type_id = ItemType.OSINT_SOURCE, source.id
        delete_url = f"/api/assess/stories/{parent.id}"
    elif kind == "report":
        parent = create_rbac_report_item("discussion")
        item_type, type_id = ItemType.REPORT_ITEM_TYPE, parent.report_item_type_id
        delete_url = f"/api/analyze/report-items/{parent.id}"
    else:
        product_type = ProductType.filter_by_title("Default TEXT Presenter")
        parent = Product(title="Discussion product", product_type_id=product_type.id)
        db.session.add(parent)
        db.session.commit()
        item_type, type_id = ItemType.PRODUCT_TYPE, product_type.id
        delete_url = f"/api/publish/products/{parent.id}"
    grant_acl(role, item_type, type_id, read_only=True)
    endpoint = f"{ROOT}/{kind}/{parent.id}"
    assert client.get(endpoint).status_code == 401
    for invalid_body in ({"body": "   "}, {"body": "Forged", "author_id": "someone-else"}):
        assert client.post(endpoint, json=invalid_body, headers=auth_header_user_permissions).status_code == 400

    for body in ("Oldest", "Second", "Third", "<b>Fourth</b>\nNew line"):
        response = client.post(endpoint, json={"body": body}, headers=auth_header_user_permissions)
        assert response.status_code == 201, response.json
        assert UUID(response.json["id"]).version == 7
    comment_url = f"{endpoint}/{response.json['id']}"
    preview = client.get(endpoint, query_string={"preview": "true"}, headers=auth_header_user_permissions).json
    assert preview["total_count"] == 4
    assert [item["body"] for item in preview["items"]] == ["Second", "Third", "<b>Fourth</b>\nNew line"]
    latest = preview["items"][-1]
    assert latest["author"] == User.find_by_name("user").name
    assert latest["can_edit"] and latest["can_delete"]
    assert latest["created_at"].endswith("+00:00")
    assert client.patch(comment_url, json={"body": "Other person's edit"}, headers=auth_header).status_code == 403
    assert client.patch(comment_url, json={"body": "Correction"}, headers=auth_header_user_permissions).status_code == 200
    revised = client.get(endpoint, headers=auth_header_user_permissions).json["items"][-1]
    assert (revised["body"], revised["created_at"]) == ("Correction", latest["created_at"])
    assert revised["edited_at"].endswith("+00:00")
    overview = client.get(ROOT, query_string={"kind": kind}, headers=auth_header_user_permissions).json["items"]
    assert [(item["parent_id"], item["excerpt"]) for item in overview] == [(parent.id, "Correction")]

    moderator_comment = client.post(endpoint, json={"body": "Admin reply"}, headers=auth_header).json["id"]
    assert client.delete(f"{endpoint}/{moderator_comment}", headers=auth_header_user_permissions).status_code == 403
    assert client.delete(comment_url, headers=auth_header).status_code == 204
    assert client.delete(delete_url, headers=auth_header).status_code == 200
    assert Comment.get(moderator_comment) is None


def test_recent_discussions_filter_access_and_keep_comments_on_merge(client, session, auth_header, auth_header_user_permissions):
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    source, survivor, _ = create_rbac_source_story("discussion-target")
    absorbed_source, absorbed, _ = create_rbac_source_story("discussion-absorbed")
    red_source, red_story, _ = create_rbac_source_story("discussion-red")
    _, hidden, _ = create_rbac_source_story("discussion-hidden")
    grant_acl(role, ItemType.OSINT_SOURCE, source.id)
    grant_acl(role, ItemType.OSINT_SOURCE, absorbed_source.id)
    grant_acl(role, ItemType.OSINT_SOURCE, red_source.id)
    red_story.upsert_attribute(NewsItemAttribute("tlp_override", "red"))
    red_story.refresh_tlp()
    db.session.commit()

    for story in (survivor, absorbed, red_story, hidden):
        response = client.post(f"{ROOT}/story/{story.id}", json={"body": story.title}, headers=auth_header)
        assert response.status_code == 201
        if story in (red_story, hidden):
            assert client.get(f"{ROOT}/story/{story.id}", headers=auth_header_user_permissions).status_code == 404
    overview = client.get(ROOT, headers=auth_header_user_permissions).json["items"]
    assert [item["parent_id"] for item in overview] == [absorbed.id, survivor.id]

    absorbed_url = f"{ROOT}/story/{absorbed.id}"
    absorbed_comment = client.get(absorbed_url, headers=auth_header_user_permissions).json["items"][0]
    response, status = Story.group_stories([survivor.id, absorbed.id])
    assert status == 200, response
    assert client.get(absorbed_url, headers=auth_header).status_code == 404
    survivor_url = f"{ROOT}/story/{survivor.id}"
    assert client.get(survivor_url, headers=auth_header_user_permissions).json["items"][-1] == absorbed_comment
    assert client.delete(f"{survivor_url}/{absorbed_comment['id']}", headers=auth_header_user_permissions).status_code == 403
    assert [item["parent_id"] for item in client.get(ROOT, headers=auth_header_user_permissions).json["items"]] == [survivor.id]
    story_data = client.get(f"/api/assess/stories/{survivor.id}", headers=auth_header).json
    assert "comments" not in story_data
