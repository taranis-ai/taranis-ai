from base64 import b64encode
from io import BytesIO

from PIL import Image


def test_thread_to_story_to_report_figure_and_withdrawal(
    client, session, api_header, auth_header, auth_header_user_permissions, tmp_path, monkeypatch
):
    from core.model.osint_source import OSINTSource
    from core.model.product import Product
    from core.model.product_type import ProductType
    from core.model.report_item import ReportItem
    from core.model.story import Story

    assert client.post("/api/worker/social/unknown", json={}, headers=auth_header).status_code == 401
    source = OSINTSource("Pilot community", "", "reddit_collector", enabled=False, parameters={"TLP_LEVEL": "clear", "PUBLISH_IMAGES": True})
    session.add(source)
    session.commit()
    endpoint = f"/api/worker/social/{source.id}"
    root = {
        "key": "t3_test",
        "thread": "t3_test",
        "title": "Service update",
        "author": "operator",
        "url": "https://www.reddit.com/r/example/comments/test",
        "published": "2026-11-19T08:00:00Z",
    }
    assert client.post(endpoint, json=root, headers=api_header).status_code == 200
    buffer = BytesIO()
    Image.new("RGB", (24, 16)).save(buffer, format="PNG")
    reply = {
        **root,
        "key": "t1_reply",
        "parent": "t3_test",
        "title": "",
        "body": "Platform reopened",
        "images": [{"key": "platform", "alt": "Station platform", "data": b64encode(buffer.getvalue()).decode()}],
    }
    post = client.post(endpoint, json=reply, headers=api_header).json
    assert client.post(endpoint, json=reply, headers=api_header).json == post
    feed = client.get("/api/assess/social", query_string={"search": "reopened", "images": "true"}, headers=auth_header).json
    assert [(r["title"], r["replies"]) for r in feed["rows"]] == [("Service update", 1)]
    assert client.post("/api/assess/social/beats", json={"name": "Rail", "sources": [source.id]}, headers=auth_header).status_code == 200
    thread = client.get(f"/api/assess/social/posts/{post['id']}", headers=auth_header).json["posts"]
    image_id = thread[1]["images"][0]["id"]
    image_url = f"/api/assess/social/images/{image_id}"
    assert client.get(image_url, headers=auth_header).data == buffer.getvalue()
    payload = {"title": "Partial restoration", "posts": [post["id"]]}
    attach = client.post("/api/assess/social/attach", json=payload, headers=auth_header)
    assert attach.status_code == 200, attach.json
    assert client.post("/api/assess/social/attach", json=payload, headers=auth_header).json == attach.json
    story = Story.get(attach.json["id"])
    assert len(story.news_items) == 1
    report = ReportItem("Outage report", None)
    report.stories = [story]
    session.add(report)
    session.commit()
    figures_url = f"/api/analyze/reports/{report.id}/figures"
    assert client.get(figures_url, headers=auth_header).json["images"][0]["eligible"]
    source.parameters = {**source.parameters, "TLP_LEVEL": "red"}
    session.commit()
    assert client.get(image_url, headers=auth_header_user_permissions).status_code == 404
    source.parameters = {**source.parameters, "TLP_LEVEL": "clear", "PUBLISH_IMAGES": False}
    session.commit()
    assert client.put(figures_url, json={"figures": [{"image_id": image_id}]}, headers=auth_header).status_code == 400
    source.parameters = {**source.parameters, "PUBLISH_IMAGES": True}
    session.commit()
    selection = {"figures": [{"image_id": image_id, "caption": "Station reopened", "alt": "Platform"}]}
    assert client.put(figures_url, json=selection, headers=auth_header).status_code == 200
    product = Product(title="Brief", product_type_id=ProductType.filter_by_title("Default PDF Presenter").id, report_items=[report.id])
    session.add(product)
    session.commit()
    render = product.to_worker_dict()
    figure = render["report_items"][0]["figures"][0]
    assert figure["caption"] == "Station reopened" and figure["src"].startswith("data:image/png;base64,")
    assert Product.update_render_for_id(product.id, b64encode(b"test product").decode(), render["render_revision"])[1] == 200
    monkeypatch.setitem(client.application.config, "DATA_FOLDER", str(tmp_path))
    assert client.post(f"/api/worker/products/{product.id}/publish", headers=api_header).status_code == 200
    public_url = f"/reports/{product.id}"
    assert client.get(public_url).data == b"test product"
    assert client.post(endpoint, json={"removed": reply["key"]}, headers=api_header).status_code == 200
    assert client.get(image_url, headers=auth_header).status_code == 404
    assert client.get(public_url).status_code == 404
    assert not (tmp_path / "published-reports" / product.id).exists()
    assert not Product.get_render(product.id)
    assert Product.update_render_for_id(product.id, "dGVzdA==", render["render_revision"])[1] == 409
