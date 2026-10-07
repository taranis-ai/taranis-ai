import io
import json
from datetime import timedelta
from pathlib import Path

import pytest

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset, AssetGroup
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun
from core.model.asset_sbom import AssetSbomComponent, AssetSbomImport
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.organization import Organization
from core.model.permission import Permission
from core.model.role import Role, TLPLevel
from core.model.role_based_access import ItemType
from core.model.story import Story
from core.model.user import User
from core.service.sbom import SbomValidationError, parse_sbom
from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story
from tests.application.support.rbac import grant_acl


FIXTURE = Path(__file__).resolve().parents[1] / "test_data/sbom/software.cdx.json"


def upload(client, headers, document=None):
    return client.post(
        "/api/assets/sbom-imports",
        headers={"Authorization": headers["Authorization"]},
        data={"file": (io.BytesIO(json.dumps(document).encode() if document is not None else FIXTURE.read_bytes()), "host.cdx.json")},
    )


@pytest.mark.parametrize("version", ["1.5", "1.6", "1.7"])
def test_cyclonedx_inventory_preserves_identity_and_coverage(version):
    document = json.loads(FIXTURE.read_bytes())
    document["specVersion"] = version
    summary, components = parse_sbom(json.dumps(document).encode())
    assert summary.software_records == 4
    assert summary.excluded_files == 1
    assert summary.component_count == 3
    assert summary.components_with_cpes == 2
    assert summary.invalid_cpe_count == 1
    openssl = next(c for c in components if c.purl == "pkg:generic/openssl@3.0.2")
    assert [o.reference for o in openssl.occurrences] == ["openssl-a", "openssl-b"]
    assert {p for o in openssl.occurrences for p in o.locations} == {"usr/lib/libssl.so", "opt/app/libssl.so"}
    assert next(c for c in components if c.purl.startswith("pkg:gem/")).cpes


@pytest.mark.parametrize("raw", [b"not json", b"[]", b'{"bomFormat":"SPDX"}', b'{"bomFormat":"CycloneDX","specVersion":"1.7","version":1}'])
def test_rejects_unsupported_or_cpe_free_documents(raw):
    with pytest.raises(SbomValidationError):
        parse_sbom(raw)


def test_asset_import_preview_confirmation_and_inventory(client, auth_header, session):
    before = db.session.query(Asset).count()
    response = upload(client, auth_header)
    assert response.status_code == 201, response.json
    preview = response.json
    assert db.session.query(Asset).count() == before
    endpoint = f"/api/assets/sbom-imports/{preview['id']}"
    assert upload(client, auth_header).json["id"] == preview["id"]
    assert client.get(endpoint, headers=auth_header).json["summary"]["component_count"] == 3
    assert client.post(endpoint, headers=auth_header, json={"name": "", "asset_group_id": "default"}).status_code == 400
    assert db.session.query(Asset).count() == before
    group = AssetGroup.get_default_group()
    created = client.post(endpoint, headers=auth_header, json={"name": "Customer portal", "asset_group_id": group.id})
    assert created.status_code == 201, created.json
    asset_id = created.json["id"]
    repeated = client.post(endpoint, headers=auth_header, json={"name": "Different name", "asset_group_id": group.id})
    assert repeated.status_code == 200
    assert repeated.json["id"] == asset_id
    assert db.session.query(Asset).count() == before + 1
    runs = db.session.scalars(db.select(AssetMatchRun).filter_by(asset_id=asset_id)).all()
    assert len(runs) == 1 and runs[0].days == 30
    asset = Asset.get(asset_id)
    assert asset.name == "Customer portal"
    assert len(asset.asset_cpes) == 2
    inventory = client.get(f"/api/assets/{asset_id}/sbom", headers=auth_header)
    assert inventory.status_code == 200
    assert inventory.json["sha256"] == preview["sha256"]
    assert inventory.json["components"] == preview["components"]
    suggestions = preview["components"][0]["suggestions"]
    assert suggestions and any(row["enabled"] for row in suggestions)
    assert client.delete(f"/api/assets/{asset_id}", headers=auth_header).status_code == 200
    assert db.session.get(AssetSbomImport, preview["id"]) is None
    assert not db.session.scalar(db.select(AssetSbomComponent).filter_by(import_id=preview["id"]))


def test_import_boundaries_persistent_preview_and_pagination(client, auth_header, auth_header_user_permissions, session):
    document = json.loads(FIXTURE.read_bytes())
    document["components"].extend({"name": f"component-{i}", "type": "library"} for i in range(55))
    response = upload(client, auth_header, document)
    assert response.status_code == 201
    endpoint = f"/api/assets/sbom-imports/{response.json['id']}"
    assert len(response.json["components"]) == 50
    assert len(client.get(endpoint + "?page=2", headers=auth_header).json["components"]) == 8
    other_user = User.find_by_name("user")
    original_roles = list(other_user.roles)
    other_user.roles = list(User.find_by_name("admin").roles)
    db.session.commit()
    assert client.get(endpoint, headers=auth_header_user_permissions).status_code == 404
    assert client.post(endpoint, headers=auth_header_user_permissions, json={}).status_code == 404
    other_user.roles = original_roles
    db.session.commit()
    other_org = Organization(name="Other SBOM organization")
    db.session.add(other_org)
    db.session.flush()
    other_group = AssetGroup(name="Private hosts", description="", organization=other_org)
    db.session.add(other_group)
    db.session.commit()
    denied = client.post(endpoint, headers=auth_header, json={"name": "Denied", "asset_group_id": other_group.id})
    assert denied.status_code == 403
    record = db.session.get(AssetSbomImport, response.json["id"])
    record.created -= timedelta(days=60)
    db.session.commit()
    assert upload(client, auth_header).status_code == 201
    assert client.get(endpoint, headers=auth_header).status_code == 200
    assert upload(client, auth_header, document).json["id"] == record.id
    assert (
        client.post(
            endpoint, headers=auth_header, json={"name": "Saved preview", "asset_group_id": AssetGroup.get_default_group().id}
        ).status_code
        == 201
    )
    assert client.get(endpoint, headers=auth_header_user_permissions).status_code == 403
    assert client.post(endpoint, headers=auth_header_user_permissions, json={}).status_code == 403


def test_asset_inventory_uses_current_organization_access(client, auth_header, session):
    preview = upload(client, auth_header).json
    user = User.find_by_name("admin")
    group = AssetGroup(name="Private SBOM", description="", organization=user.organization)
    db.session.add(group)
    db.session.commit()
    created = client.post(
        f"/api/assets/sbom-imports/{preview['id']}", headers=auth_header, json={"name": "Private", "asset_group_id": group.id}
    )
    assert created.status_code == 201
    organization = Organization(name="New SBOM owner")
    db.session.add(organization)
    db.session.flush()
    group.organization = organization
    db.session.commit()
    assert client.get(f"/api/assets/{created.json['id']}/sbom", headers=auth_header).status_code == 404
    assert client.get(f"/api/assets/sbom-imports/{preview['id']}", headers=auth_header).status_code == 404
    for suffix in ("triggers", "intelligence", "match-runs"):
        assert client.get(f"/api/assets/{created.json['id']}/{suffix}", headers=auth_header).status_code == 404
    assert client.post(f"/api/assets/{created.json['id']}/triggers/suggestions", headers=auth_header).status_code == 404


def test_import_retains_asset_when_initial_scan_cannot_be_queued(client, auth_header, session, monkeypatch):
    preview = upload(client, auth_header).json
    endpoint = f"/api/assets/sbom-imports/{preview['id']}"
    with monkeypatch.context() as patch:
        patch.setattr(queue_manager.queue_manager, "enqueue_task", lambda *args, **kwargs: False)
        created = client.post(endpoint, headers=auth_header, json={"name": "Saved host", "asset_group_id": AssetGroup.get_default_group().id})
    assert created.status_code == 201
    base = f"/api/assets/{created.json['id']}"
    assert client.get(base + "/sbom", headers=auth_header).status_code == 200
    run = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert run["status"] == "FAILED" and run["error"] == "Unable to queue the scan. Please try again."
    retry = client.post(base + "/match-runs", headers=auth_header, json={"days": 30})
    assert retry.status_code == 202 and retry.json["status"] == "QUEUED"


def test_import_without_intelligence_access_does_not_start_scan(client, auth_header_user_permissions, session):
    role = Role.filter_by_name("User")
    role.permissions = Permission.get_bulk(["ASSETS_ACCESS", "ASSETS_CREATE"])
    db.session.commit()
    preview = upload(client, auth_header_user_permissions).json
    created = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header_user_permissions,
        json={"name": "Inventory only", "asset_group_id": AssetGroup.get_default_group().id},
    )
    assert created.status_code == 201
    assert not db.session.scalar(db.select(AssetMatchRun).filter_by(asset_id=created.json["id"]))
    assert client.get(f"/api/assets/{created.json['id']}/intelligence", headers=auth_header_user_permissions).status_code == 403


def test_component_trigger_review_collection_and_explainable_matches(client, auth_header, api_header, session):
    source = create_osint_source(rank=0)
    original = build_news_item_payload(source.id, title="OpenSSL advisory", content="Python requests and OpenSSL are discussed.")
    assert client.post("/api/worker/news-items", headers=api_header, json=[original]).status_code == 200
    document = json.loads(FIXTURE.read_bytes())
    document["components"].extend(
        {"name": "requests", "type": "library", "version": version, "purl": f"pkg:pypi/requests@{version}"}
        for version in ("2.32.0", "2.32.1")
    )
    document["components"].append(document["components"][0] | {"bom-ref": "vendor-openssl", "purl": "pkg:generic/vendor/openssl@3.0.2"})
    preview = upload(client, auth_header, document).json
    asset_id = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header,
        json={"name": "Intelligence portal", "asset_group_id": AssetGroup.get_default_group().id},
    ).json["id"]
    base = f"/api/assets/{asset_id}"
    triggers = client.get(base + "/triggers", headers=auth_header).json["items"]
    assert not next(t for t in triggers if t["phrase"] == "ruby-lang")["enabled"]
    requests = next(t for t in triggers if t["phrase"] == "requests")
    assert requests["enabled"] and requests["context"] == ["Python"] and not requests["has_cpe"]
    openssl = [t for t in triggers if t["phrase"] == "openssl"]
    assert len(openssl) == 3
    assert all(t["enabled"] for t in openssl)
    assert set(openssl[0]["sources"]) == {"sbom", "cpe"}
    assert client.get(base + "/intelligence", headers=auth_header).json["items"] == []

    selected = [requests["id"], *[t["id"] for t in openssl]]
    scan = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert scan["status"] == "QUEUED" and scan["days"] == 30
    batch_url = f"/api/worker/asset-match-runs/{scan['id']}/batch"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "COMPLETED"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "COMPLETED"
    matches = client.get(base + "/intelligence", headers=auth_header).json["items"]
    assert len(matches) == 1 and matches[0]["software_count"] == 4
    assert len(matches[0]["articles"]) == 1
    article = matches[0]["articles"][0]
    assert article["id"] == original["id"]
    assert len(article["software"]) == 4
    assert {c["purl"] for p in article["software"] for c in p["components"] if p["name"] == "openssl"} == {
        "pkg:generic/openssl@3.0.2",
        "pkg:gem/openssl@3.0.2",
        "pkg:generic/vendor/openssl@3.0.2",
    }
    package = next(p for p in article["software"] if p["name"] == "requests")
    assert package["versions"] == ["2.32.0", "2.32.1"]
    assert len(article["evidence"]) == 2
    content = next(e for e in article["evidence"] if e["field"] == "content")
    assert content["excerpt"] == original["content"]
    assert len(content["matches"]) == 4
    reason = next(r for r in content["matches"] if r["phrase"] == "requests")
    assert reason["matched_text"] == "requests" and reason["context"] == ["Python"]
    assert reason["software_id"] == package["id"]
    assert {t["component_id"] for t in reason["triggers"]} == {c["id"] for c in package["components"]}
    assert {t["version"] for t in reason["triggers"]} == {"2.32.0", "2.32.1"}
    assert db.session.query(AssetArticleMatch).count() == 5
    assert not Asset.get(asset_id).vulnerabilities

    # Context must be in the same article, and substrings/HTML attributes are not evidence.
    unrelated = build_news_item_payload(source.id, title="Feature requests", content='<p>OpenSSLish requests</p><a title="Python">Plans</a>')
    assert client.post("/api/worker/news-items", headers=api_header, json=[unrelated]).status_code == 200
    assert len(client.get(base + "/intelligence", headers=auth_header).json["items"]) == 1
    corrected = unrelated | {"title": original["title"], "content": "<p>Python REQUESTS uses TLS.</p>"}
    assert client.post("/api/worker/news-items", headers=api_header, json=[corrected]).status_code == 200
    assert len(client.get(base + "/intelligence", headers=auth_header).json["items"]) == 2
    Story.group_stories([NewsItem.get(original["id"]).story_id, NewsItem.get(unrelated["id"]).story_id])
    grouped = client.get(base + "/intelligence", headers=auth_header).json["items"]
    assert len(grouped) == 1 and grouped[0]["software_count"] == 4
    assert {a["id"] for a in grouped[0]["articles"]} == {original["id"], unrelated["id"]}
    assert [a["title"] for a in grouped[0]["articles"]] == [original["title"], original["title"]]

    custom = client.post(
        base + "/triggers",
        headers=auth_header,
        json={
            "component_id": requests["component_id"],
            "phrase": "Python requests",
            "context": ["discussed"],
            "enabled": True,
        },
    )
    assert custom.status_code == 201 and custom.json["sources"] == ["analyst"]
    rescan = client.post(base + "/match-runs", headers=auth_header, json={"days": 0}).json
    assert client.post(f"/api/worker/asset-match-runs/{rescan['id']}/batch", headers=api_header, json={}).json["status"] == "COMPLETED"
    grouped = client.get(base + "/intelligence", headers=auth_header).json["items"]
    article = next(a for a in grouped[0]["articles"] if a["id"] == original["id"])
    assert len(article["software"]) == 4 and len(article["evidence"]) == 2
    content = next(e for e in article["evidence"] if e["field"] == "content")
    assert {(r["phrase"], tuple(r["context"])) for r in content["matches"] if r["software_id"] == package["id"]} == {
        ("requests", ("Python",)),
        ("Python requests", ("discussed",)),
    }
    selected.append(custom.json["id"])
    edited = {"phrase": "SSL library", "context": ["OpenSSL"], "enabled": False}
    assert client.put(base + f"/triggers/{openssl[0]['id']}", headers=auth_header, json=edited).status_code == 200
    remaining = client.get(base + "/intelligence", headers=auth_header).json["items"][0]
    assert remaining["software_count"] == 3
    for article in remaining["articles"]:
        assert len(article["software"]) == 3
        assert openssl[0]["component_id"] not in {c["id"] for p in article["software"] for c in p["components"]}
        assert openssl[0]["id"] not in {t["id"] for e in article["evidence"] for r in e["matches"] for t in r["triggers"]}
    assert client.post(base + "/triggers/suggestions", headers=auth_header, json={}).json["added"] == 0
    saved = client.get(base + "/triggers", headers=auth_header).json["items"]
    assert next(t for t in saved if t["id"] == openssl[0]["id"])["phrase"] == "SSL library"
    assert client.post(base + "/triggers/selection", headers=auth_header, json={"trigger_ids": selected, "enabled": False}).status_code == 200
    assert client.get(base + "/intelligence", headers=auth_header).json["items"] == []


def test_intelligence_paginates_complete_stories(client, auth_header, api_header, session):
    preview = upload(client, auth_header).json
    asset_id = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header,
        json={"name": "Paged intelligence", "asset_group_id": AssetGroup.get_default_group().id},
    ).json["id"]
    source = create_osint_source(rank=0)
    articles = [build_news_item_payload(source.id, title=f"OpenSSL notice {i}") for i in range(22)]
    assert client.post("/api/worker/news-items", headers=api_header, json=articles).status_code == 200
    Story.group_stories([NewsItem.get(article["id"]).story_id for article in articles[:2]])
    expected_ids = sorted({NewsItem.get(article["id"]).story_id for article in articles}, reverse=True)

    endpoint = f"/api/assets/{asset_id}/intelligence"
    first = client.get(endpoint, headers=auth_header).json
    second = client.get(endpoint + "?page=2", headers=auth_header).json
    assert [story["id"] for story in first["items"]] == expected_ids[:20]
    assert [story["id"] for story in second["items"]] == expected_ids[20:]
    assert first["has_more"] and not second["has_more"]
    stories = first["items"] + second["items"]
    assert sum(len(story["articles"]) for story in stories) == 22
    for story in stories:
        assert story["software_count"] == 2
        for article in story["articles"]:
            assert len(article["software"]) == 2
            assert len(article["evidence"]) == 1
            assert len(article["evidence"][0]["matches"]) == 2
    empty = client.get(endpoint + "?page=3", headers=auth_header).json
    assert empty["items"] == [] and not empty["has_more"]


def test_historical_matching_batches_and_current_visibility(client, auth_header, auth_header_user_permissions, api_header, session):
    preview = upload(client, auth_header).json
    asset_id = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header,
        json={"name": "Scoped intelligence", "asset_group_id": AssetGroup.get_default_group().id},
    ).json["id"]
    base = f"/api/assets/{asset_id}"
    triggers = client.get(base + "/triggers?search=openssl", headers=auth_header).json["items"]
    assert (
        client.post(
            base + "/triggers/selection", headers=auth_header, json={"trigger_ids": [t["id"] for t in triggers], "enabled": False}
        ).status_code
        == 200
    )
    trigger = triggers[0]
    assert (
        client.put(base + f"/triggers/{trigger['id']}", headers=auth_header, json={"phrase": "OpenSSL", "enabled": True}).status_code == 200
    )
    source = create_osint_source(rank=0)
    story = create_story(news_items=[build_news_item_payload(source.id, title=f"OpenSSL notice {i}") for i in range(201)])
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS", "ASSETS_CREATE"]) if p not in role.permissions)
    acl = grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
    scan = client.post(base + "/match-runs", headers=auth_header_user_permissions, json={"days": 30})
    assert scan.status_code == 202, scan.json
    batch_url = f"/api/worker/asset-match-runs/{scan.json['id']}/batch"
    first = client.post(batch_url, headers=api_header, json={}).json
    assert first["status"] == "RUNNING" and first["processed"] == 200
    final = client.post(batch_url, headers=api_header, json={}).json
    assert final["status"] == "COMPLETED" and final["processed"] == 201
    assert client.get(base + "/match-runs", headers=auth_header).json["run"]["id"] != scan.json["id"]
    visible_story = client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"][0]
    assert len(visible_story["articles"]) == 201 and visible_story["software_count"] == 1
    acl.item_id = "unavailable"
    db.session.commit()
    assert client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"] == []
    acl.item_id = source.id
    story.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    assert client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"] == []
    story.upsert_attribute(NewsItemAttribute(key="TLP", value="clear"))
    story.news_items[0].upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    visible_story = client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"][0]
    assert len(visible_story["articles"]) == 200 and visible_story["software_count"] == 1
    assert story.news_items[0].id not in {a["id"] for a in visible_story["articles"]}
    # A scan must recheck permissions when the worker runs, not only when it was queued.
    scan = client.post(base + "/match-runs", headers=auth_header_user_permissions, json={"days": 0})
    role.permissions = [p for p in role.permissions if p.code != "ASSESS_ACCESS"]
    db.session.commit()
    batch_url = f"/api/worker/asset-match-runs/{scan.json['id']}/batch"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "FAILED"
    assert db.session.get(AssetMatchRun, scan.json["id"]).processed == 0
    assert client.get(base + "/intelligence", headers=auth_header_user_permissions).status_code == 403
