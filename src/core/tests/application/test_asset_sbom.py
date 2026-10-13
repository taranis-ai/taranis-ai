import io
import json
import os
from datetime import timedelta
from pathlib import Path

import pytest
from models.sbom_parser import SbomValidationError, parse_sbom

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.asset import Asset, AssetCpe, AssetGroup, AssetObservable, AssetTag
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent, AssetSbomFindingComponent, AssetSbomImport, AssetSbomUpload, AssetSbomUploadReference
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.news_item_tag import NewsItemTag
from core.model.organization import Organization
from core.model.permission import Permission
from core.model.role import Role, TLPLevel
from core.model.role_based_access import ItemType
from core.model.story import Story
from core.model.user import User
from tests.application.support.builders import build_news_item_payload, create_osint_source, create_story
from tests.application.support.rbac import grant_acl


FIXTURE = Path(__file__).resolve().parents[1] / "test_data/sbom/software.cdx.json"


def upload(client, headers, document=None):
    response = client.post(
        "/api/assets/sbom-imports",
        headers={"Authorization": headers["Authorization"]},
        data={"file": (io.BytesIO(json.dumps(document).encode() if document is not None else FIXTURE.read_bytes()), "host.cdx.json")},
    )
    assert response.status_code in (200, 202), response.json
    if response.json["status"] != "READY":
        prepare_upload(client, response.json["id"])
    progress = client.get(f"/api/assets/sbom-uploads/{response.json['id']}", headers=headers)
    return client.get(f"/api/assets/sbom-imports/{progress.json['import_id']}", headers=headers)


def prepare_upload(client, upload_id):
    from models.sbom import SBOM_BATCH_SIZE

    worker_headers = {"Authorization": f"Bearer {os.getenv('API_KEY')}"}
    endpoint = f"/api/worker/sbom-uploads/{upload_id}"
    source = client.get(endpoint, headers=worker_headers)
    assert source.status_code == 200
    parsed = parse_sbom(source.data)
    response = client.post(endpoint + "/begin", headers=worker_headers, json=parsed.summary.model_dump())
    assert response.status_code == 200, response.json
    for kind, items in (("components", parsed.components), ("findings", parsed.findings)):
        for offset in range(0, len(items), SBOM_BATCH_SIZE):
            response = client.post(
                endpoint + "/" + kind,
                headers=worker_headers,
                json={"offset": offset, "items": [item.model_dump() for item in items[offset : offset + SBOM_BATCH_SIZE]]},
            )
            assert response.status_code == 200, response.json
    response = client.post(endpoint + "/complete", headers=worker_headers, json={})
    assert response.status_code == 200, response.json


@pytest.mark.parametrize("version", ["1.5", "1.6", "1.7"])
def test_cyclonedx_inventory_preserves_identity_and_coverage(version):
    document = json.loads(FIXTURE.read_bytes())
    document["specVersion"] = version
    parsed = parse_sbom(json.dumps(document).encode())
    summary, components = parsed.summary, parsed.components
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


@pytest.mark.parametrize(
    ("source_name", "suggested_name"),
    [
        ("SBOMProber / spwebcam", "spwebcam"),
        ("\u00a0SBOMProber\u00a0/\u00a0spwebcam\u00a0", "spwebcam"),
        ("Group / host / subsystem", "host / subsystem"),
        ("  spwebcam  ", "spwebcam"),
        ("path/to/host", "path/to/host"),
        (" / spwebcam", "/ spwebcam"),
        ("Group / ", "Group /"),
    ],
)
def test_import_suggests_shorter_name_and_preserves_source(source_name, suggested_name):
    document = json.loads(FIXTURE.read_bytes())
    document["metadata"]["component"]["name"] = source_name
    summary = parse_sbom(json.dumps(document).encode()).summary
    assert summary.suggested_name == suggested_name
    assert summary.source_name == source_name


def test_asset_import_preview_confirmation_and_inventory(client, auth_header, session):
    before = db.session.query(Asset).count()
    response = upload(client, auth_header)
    assert response.status_code == 200, response.json
    preview = response.json
    assert db.session.query(Asset).count() == before
    endpoint = f"/api/assets/sbom-imports/{preview['id']}"
    assert upload(client, auth_header).json["id"] == preview["id"]
    assert client.get(endpoint, headers=auth_header).json["summary"]["component_count"] == 3
    assert client.post(endpoint, headers=auth_header, json={"name": "", "asset_group_id": "default"}).status_code == 400
    assert db.session.query(Asset).count() == before
    group = AssetGroup.get_default_group()
    created = client.post(
        endpoint,
        headers=auth_header,
        json={"name": "Customer portal", "asset_group_id": group.id, "tags": [" SBOMProber ", "SBOMPROBER", "sbomprober_network", ""]},
    )
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
    assert client.get(f"/api/assets/{asset_id}", headers=auth_header).json["tags"] == ["sbomprober", "sbomprober_network"]
    assert len(asset.asset_cpes) == 2
    inventory = client.get(f"/api/assets/{asset_id}/sbom", headers=auth_header)
    assert inventory.status_code == 200
    assert inventory.json["sha256"] == preview["sha256"]
    assert inventory.json["components"] == preview["components"]
    suggestions = preview["components"][0]["suggestions"]
    assert suggestions and any(row["enabled"] for row in suggestions)
    assert client.delete(f"/api/assets/{asset_id}", headers=auth_header).status_code == 200
    assert not db.session.scalar(db.select(AssetTag).filter_by(asset_id=asset_id))
    assert db.session.get(AssetSbomImport, preview["id"]) is None
    assert not db.session.scalar(db.select(AssetSbomComponent).filter_by(import_id=preview["id"]))


def test_import_boundaries_persistent_preview_and_pagination(client, auth_header, auth_header_user_permissions, session):
    document = json.loads(FIXTURE.read_bytes())
    document["components"].extend({"name": f"component-{i}", "type": "library"} for i in range(55))
    response = upload(client, auth_header, document)
    assert response.status_code == 200
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
    assert upload(client, auth_header).status_code == 200
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


@pytest.mark.parametrize("cve_only", [False, True])
def test_intelligence_paginates_complete_stories(client, auth_header, api_header, session, cve_only):
    document = json.loads(FIXTURE.read_bytes())
    document["vulnerabilities"] = [{"id": "CVE-2026-12345", "affects": [{"ref": "openssl-a"}]}]
    preview = upload(client, auth_header, document).json
    asset_id = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header,
        json={"name": "Paged intelligence", "asset_group_id": AssetGroup.get_default_group().id},
    ).json["id"]
    source = create_osint_source(rank=0)
    articles = [build_news_item_payload(source.id, title=f"OpenSSL notice {i}") for i in range(22)]
    for article in articles:
        article["tags"] = {"CVE-2026-12345": "CVE"}
    assert client.post("/api/worker/news-items", headers=api_header, json=articles).status_code == 200
    Story.group_stories([NewsItem.get(article["id"]).story_id for article in articles[:2]])
    expected_ids = sorted({NewsItem.get(article["id"]).story_id for article in articles}, reverse=True)

    if cve_only:
        untagged = [build_news_item_payload(source.id, title=f"OpenSSL product announcement {i}") for i in range(22)]
        assert client.post("/api/worker/news-items", headers=api_header, json=untagged).status_code == 200
    endpoint = f"/api/assets/{asset_id}/intelligence?cve_only={'true' if cve_only else 'false'}"
    first = client.get(endpoint, headers=auth_header).json
    second = client.get(endpoint + "&page=2", headers=auth_header).json
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
    empty = client.get(endpoint + "&page=3", headers=auth_header).json
    assert empty["items"] == [] and not empty["has_more"]
    assert client.put(f"/api/assets/{asset_id}", headers=auth_header, json={"tags": ["paged"]}).status_code == 201
    overview = "/api/assets/intelligence?cve_match=yes&tag=paged"
    first = client.get(overview, headers=auth_header).json
    second = client.get(overview + "&page=2", headers=auth_header).json
    assert [story["id"] for story in first["items"]] == expected_ids[:20]
    assert [story["id"] for story in second["items"]] == expected_ids[20:]
    assert first["has_more"] and not second["has_more"]


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


@pytest.fixture
def finding_document():
    return json.loads(FIXTURE.with_name("test-sbom-findings.cdx.json").read_text())


def import_findings(client, headers, document):
    preview = upload(client, headers, document).json
    created = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=headers,
        json={"name": "Finding showcase", "asset_group_id": AssetGroup.get_default_group().id},
    )
    assert created.status_code == 201, created.json
    return preview, f"/api/assets/{created.json['id']}"


def test_imported_findings_cti_and_live_tag_associations(
    client, auth_header, auth_header_user_permissions, api_header, session, finding_document
):
    source = create_osint_source(rank=0)
    story = create_story(
        news_items=[
            build_news_item_payload(source.id, title="BuildKit security bulletin"),
            build_news_item_payload(source.id, title="Second bulletin"),
            build_news_item_payload(source.id, title="internal-agent product announcement"),
        ]
    )
    for item in story.news_items[:2]:
        item.tags.append(NewsItemTag(" (cve-2026-12345) ", "cves"))
    # Duplicate tags must not duplicate the article or its CVE association.
    story.news_items[0].tags.append(NewsItemTag("CVE-2026-12345", "CVE"))
    db.session.commit()
    preview, base = import_findings(client, auth_header, finding_document)
    assert preview["summary"]["finding_count"] == 2
    assert preview["summary"]["affected_component_count"] == 4
    assert preview["summary"]["unresolved_reference_count"] == 1
    cti = client.get(base + "/cti", headers=auth_header).json
    assert cti["pagination"]["total"] == 2
    cve = next(i for i in cti["iocs"] if i["value"] == "CVE-2026-12345")
    finding = cve["findings"][0]
    assert finding["records"] == finding_document["vulnerabilities"][:2]
    assert len(finding["components"]) == 3
    assert finding["unresolved_references"] == ["unresolved-curl"]
    assert set(cve["news_item_ids"]) == {item.id for item in story.news_items[:2]}
    assert Asset.get(base.rsplit("/", 1)[1]).vulnerabilities_count == 0
    # Existing CVE tags match immediately, before a product-name scan.
    results = client.get(base + "/intelligence", headers=auth_header).json["items"]
    assert len(results) == 1 and len(results[0]["articles"]) == 2
    assert results[0]["software_count"] == 2
    assert all(len(a["cve_matches"]) == 1 and not a["evidence"] for a in results[0]["articles"])
    run = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert client.post(f"/api/worker/asset-match-runs/{run['id']}/batch", headers=api_header, json={}).status_code == 200
    results = client.get(base + "/intelligence", headers=auth_header).json["items"]
    article = next(a for a in results[0]["articles"] if a["title"] == "BuildKit security bulletin")
    assert article["evidence"] and len(article["software"]) == 2 and len(article["cve_matches"]) == 1
    assert len(results[0]["articles"]) == 3 and results[0]["software_count"] == 3
    filtered = base + "/intelligence?cve_only=true"
    results = client.get(filtered, headers=auth_header).json["items"]
    assert len(results[0]["articles"]) == 2 and results[0]["software_count"] == 2
    assert article in results[0]["articles"]
    triggers = client.get(base + "/triggers", headers=auth_header).json["items"]
    client.post(base + "/triggers/selection", headers=auth_header, json={"trigger_ids": [t["id"] for t in triggers], "enabled": False})
    assert len(client.get(base + "/intelligence", headers=auth_header).json["items"][0]["articles"]) == 2
    toggle = base + "/sbom/cves/CVE-2026-12345"
    assert client.put(toggle, headers=auth_header, json={"enabled": False}).status_code == 200
    assert client.get(base + "/intelligence", headers=auth_header).json["items"] == []
    assert client.get(filtered, headers=auth_header).json["items"] == []
    disabled = client.get(base + "/cti?search=12345", headers=auth_header).json["iocs"][0]
    assert not disabled["findings"][0]["matching_enabled"] and not disabled["news_item_ids"]
    client.put(toggle, headers=auth_header, json={"enabled": True})
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS"]) if p not in role.permissions)
    acl = grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
    db.session.commit()
    assert len(client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"]) == 1
    story.news_items[0].upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    visible = client.get(base + "/cti?search=12345", headers=auth_header_user_permissions).json["iocs"][0]
    assert visible["news_item_ids"] == [story.news_items[1].id]
    articles = client.get(filtered, headers=auth_header_user_permissions).json["items"][0]["articles"]
    assert [article["id"] for article in articles] == [story.news_items[1].id]
    acl.item_id = "unavailable"
    db.session.commit()
    assert client.get(base + "/intelligence", headers=auth_header_user_permissions).json["items"] == []
    assert client.get(filtered, headers=auth_header_user_permissions).json["items"] == []
    assert not client.get(base + "/cti?search=12345", headers=auth_header_user_permissions).json["iocs"][0]["news_item_ids"]
    for item in story.news_items:
        for tag in item.tags:
            db.session.delete(tag)
    db.session.commit()
    assert client.get(base + "/intelligence", headers=auth_header).json["items"] == []
    assert client.get(filtered, headers=auth_header).json["items"] == []


def test_replacement_preserves_decisions_and_removes_obsolete_snapshot(client, auth_header, api_header, session, finding_document):
    preview, base = import_findings(client, auth_header, finding_document)
    asset = Asset.get(base.rsplit("/", 1)[1])
    asset.name, asset.serial, asset.description = "Manually named host", "asset-123", "Maintained description"
    asset.set_tags(["sbomprober", "sbomprober_network"])
    asset.asset_observables.append(AssetObservable("domain", "example.invalid"))
    manual_cpe = "cpe:2.3:a:manual:software:1:*:*:*:*:*:*:*"
    asset.asset_cpes.append(AssetCpe(manual_cpe))
    db.session.commit()
    original_group = asset.asset_group_id
    triggers = client.get(base + "/triggers", headers=auth_header).json["items"]
    buildkit = next(t for t in triggers if t["phrase"] == "buildkit")
    client.put(
        base + f"/triggers/{buildkit['id']}", headers=auth_header, json={"phrase": "BuildKit", "context": ["security"], "enabled": False}
    )
    old_run = client.get(base + "/match-runs", headers=auth_header).json["run"]
    source = create_osint_source(rank=0)
    payload = build_news_item_payload(source.id, title="curl and internal-agent security notice")
    assert client.post("/api/worker/news-items", headers=api_header, json=[payload]).status_code == 200
    assert db.session.query(AssetArticleMatch).count() == 2
    client.put(base + "/sbom/cves/CVE-2026-12345", headers=auth_header, json={"enabled": False})
    replacement = json.loads(json.dumps(finding_document))
    replacement["components"] = [c for c in replacement["components"] if c["bom-ref"] != "curl"]
    replacement["components"].append(
        {
            **replacement["components"][0],
            "bom-ref": "buildkit-new",
            "version": "v0.33.0",
            "purl": "pkg:golang/github.com/moby/buildkit@v0.33.0",
            "cpe": "cpe:2.3:a:moby:buildkit:v0.33.0:*:*:*:*:*:*:*",
        }
    )
    replacement["vulnerabilities"] = [replacement["vulnerabilities"][0]]
    replacement["vulnerabilities"][0]["affects"].append({"ref": "buildkit-new"})
    new = upload(client, auth_header, replacement).json
    comparison = client.get(f"/api/assets/sbom-imports/{new['id']}?asset_id={asset.id}", headers=auth_header).json["comparison"]
    assert comparison["components_added"] == 1 and comparison["components_removed"] == 1
    assert comparison["cves_removed"] == 1 and comparison["expected_sha256"] == preview["sha256"]
    body = {"import_id": new["id"], "expected_sha256": "stale"}
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 409
    assert client.get(base + "/sbom", headers=auth_header).json["id"] == preview["id"]
    body["expected_sha256"] = preview["sha256"]
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 200
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 200
    assert db.session.get(AssetSbomImport, preview["id"]) is None
    remaining_matches = db.session.scalars(db.select(AssetArticleMatch)).all()
    assert len(remaining_matches) == 1 and remaining_matches[0].trigger.component.inventory["name"] == "internal-agent"
    assert remaining_matches[0].trigger.component.import_id == new["id"]
    assert db.session.get(AssetMatchRun, old_run["id"]).status == "SUPERSEDED"
    assert client.post(f"/api/worker/asset-match-runs/{old_run['id']}/batch", headers=api_header, json={}).json["status"] == "SUPERSEDED"
    assert len(db.session.scalars(db.select(AssetMatchRun).where(AssetMatchRun.asset_id == asset.id)).all()) == 2
    db.session.refresh(asset)
    assert client.get(base, headers=auth_header).json["tags"] == ["sbomprober", "sbomprober_network"]
    assert (asset.name, asset.serial, asset.description, asset.asset_group_id) == (
        "Manually named host",
        "asset-123",
        "Maintained description",
        original_group,
    )
    assert [o.value for o in asset.asset_observables] == ["example.invalid"]
    assert manual_cpe in {c.value for c in asset.asset_cpes}
    assert not any(":curl:" in c.value for c in asset.asset_cpes)
    rules = client.get(base + "/triggers?search=BuildKit", headers=auth_header).json["items"]
    inherited = next(t for t in rules if t["phrase"] == "BuildKit")
    assert inherited["versions"] == ["v0.32.0", "v0.32.1", "v0.33.0"]
    assert not inherited["enabled"] and inherited["context"] == ["security"]
    assert db.session.get(AssetTrigger, buildkit["id"]) is not None
    cti = client.get(base + "/cti?search=12345", headers=auth_header).json["iocs"][0]
    assert not cti["findings"][0]["matching_enabled"] and len(cti["findings"][0]["components"]) == 3
    # A subsequent inventory-only export explicitly warns that findings will be cleared.
    versions = db.session.scalars(db.select(AssetTrigger).where(AssetTrigger.phrase == "BuildKit")).all()
    versions[0].enabled = True
    db.session.commit()
    replacement["components"].append(
        {
            **replacement["components"][0],
            "bom-ref": "buildkit-conflicting",
            "version": "v0.34.0",
            "purl": "pkg:golang/github.com/moby/buildkit@v0.34.0",
        }
    )
    replacement.pop("vulnerabilities")
    no_findings = upload(client, auth_header, replacement).json
    comparison = client.get(f"/api/assets/sbom-imports/{no_findings['id']}?asset_id={asset.id}", headers=auth_header).json["comparison"]
    assert comparison["clears_findings"] and not no_findings["summary"]["vulnerabilities_supplied"]
    assert (
        client.put(base + "/sbom", headers=auth_header, json={"import_id": no_findings["id"], "expected_sha256": new["sha256"]}).status_code
        == 200
    )
    assert not client.get(base + "/cti?search=CVE", headers=auth_header).json["iocs"]
    assert db.session.query(AssetSbomFindingComponent).count() == 0
    conflicts = client.get(base + "/triggers?search=BuildKit", headers=auth_header).json["items"]
    review = next(t for t in conflicts if "v0.34.0" in t["versions"] and t["phrase"] == "BuildKit")
    assert review["review_required"] and not review["enabled"]
    reviewed = client.put(
        base + f"/triggers/{review['id']}", headers=auth_header, json={"phrase": "BuildKit", "context": ["security"], "enabled": True}
    )
    assert reviewed.status_code == 200 and not reviewed.json["review_required"]
    replacement["vulnerabilities"] = []
    empty = upload(client, auth_header, replacement).json
    assert empty["summary"]["vulnerabilities_supplied"] and empty["summary"]["finding_count"] == 0


def test_asset_cti_pagination_component_search_and_inventory_upgrade(client, auth_header, session, finding_document):
    finding_document["vulnerabilities"].extend({"id": f"CVE-2026-{20000 + i}", "affects": [{"ref": "curl"}]} for i in range(51))
    preview, base = import_findings(client, auth_header, finding_document)
    first = client.get(base + "/cti", headers=auth_header).json
    second = client.get(base + "/cti?page=2", headers=auth_header).json
    assert first["pagination"] == {"page": 1, "pages": 2, "total": 53, "search": ""}
    assert len(first["iocs"]) == 50 and len(second["iocs"]) == 3
    assert {i["value"] for i in first["iocs"]}.isdisjoint(i["value"] for i in second["iocs"])
    assert client.get(base + "/cti?search=curl", headers=auth_header).json["pagination"]["total"] == 52
    assert client.get("/api/assets/cti?search=CVE-2026&page=2", headers=auth_header).json["pagination"] == {
        "page": 2,
        "pages": 2,
        "total": 53,
        "search": "CVE-2026",
    }
    overview = client.get("/api/assets/cti?search=12345", headers=auth_header).json
    assert overview["iocs"][0]["findings"][0]["asset_id"] == base.rsplit("/", 1)[1]
    # Old importer snapshots have no parser revision and discarded the same file's findings.
    record = db.session.get(AssetSbomImport, preview["id"])
    record.summary = {key: value for key, value in record.summary.items() if key != "parser_version"}
    record.findings.clear()
    db.session.commit()
    upgrade = upload(client, auth_header, finding_document).json
    assert upgrade["id"] != preview["id"] and upgrade["sha256"] == preview["sha256"]
    assert (
        client.put(base + "/sbom", headers=auth_header, json={"import_id": upgrade["id"], "expected_sha256": preview["sha256"]}).status_code
        == 200
    )
    assert client.get(base + "/cti", headers=auth_header).json["pagination"]["total"] == 53


def test_intelligence_overview_filters_each_host_and_preserves_score_provenance(
    client, auth_header, auth_header_user_permissions, api_header, session, finding_document
):
    source = create_osint_source(rank=0)
    story = create_story(
        news_items=[
            build_news_item_payload(source.id, title="BuildKit security bulletin"),
            build_news_item_payload(source.id, title="Vendor bulletin"),
            build_news_item_payload(source.id, title="curl product announcement"),
        ]
    )
    both, tagged, product = story.news_items
    both.tags.append(NewsItemTag("CVE-2026-12345", "CVE"))
    tagged.tags.append(NewsItemTag("CVE-2026-12346", "CVE"))
    db.session.commit()
    # Non-CVSS ratings and unrelated findings cannot supply a matching score.
    finding_document["vulnerabilities"][2]["ratings"] = [{"score": 9.9, "method": "other"}]
    finding_document["vulnerabilities"].append(
        {"id": "CVE-2026-99999", "affects": [{"ref": "internal-agent"}], "ratings": [{"score": 10, "method": "CVSSv4"}]}
    )
    _, first_base = import_findings(client, auth_header, finding_document)
    other_document = json.loads(json.dumps(finding_document))
    other_document["vulnerabilities"] = [
        {
            "id": "CVE-2026-12346",
            "affects": [{"ref": "internal-agent"}],
            "ratings": [{"score": 0, "method": "CVSSv4", "source": {"name": "Vendor"}}],
        }
    ]
    _, second_base = import_findings(client, auth_header, other_document)
    first, second = [Asset.get(base.rsplit("/", 1)[1]) for base in (first_base, second_base)]
    first.name, second.name = "Host A", "Host B"
    first.set_tags(["sbomprober", "sbomprober_network"])
    second.set_tags(["sbomprober", "private-host"])
    group = AssetGroup("Second host group", "", User.find_by_name("admin").organization)
    db.session.add(group)
    db.session.flush()
    second.asset_group = group
    db.session.commit()
    for base in (first_base, second_base):
        run = client.get(base + "/match-runs", headers=auth_header).json["run"]
        assert client.post(f"/api/worker/asset-match-runs/{run['id']}/batch", headers=api_header, json={}).status_code == 200

    endpoint = "/api/assets/intelligence"
    data = client.get(endpoint, headers=auth_header).json
    articles = {a["id"]: a for a in data["items"][0]["articles"]}
    assert set(articles) == {both.id, tagged.id, product.id}
    assert all(len(a["hosts"]) == 2 for a in articles.values())
    assert articles[both.id]["cve_count"] == articles[tagged.id]["cve_count"] == 1
    hosts = articles[both.id]["hosts"]
    assert [(h["asset_name"], h["max_cvss"], h["package_match"]) for h in hosts] == [("Host A", 9.1, True), ("Host B", None, True)]
    assert len(hosts[0]["software"]) == 2 and len(hosts[0]["cve_matches"]) == 1
    ratings = hosts[0]["cve_matches"][0]["ratings"]
    assert {r["source"]["name"] for r in ratings} == {"NVD", "Vendor advisory"}
    assert {r["method"] for r in ratings} == {"CVSSv2", "CVSSv31"}

    scored = client.get(endpoint, headers=auth_header, query_string={"cve_match": "yes", "cvss_min": 7}).json["items"][0]["articles"]
    assert [a["id"] for a in scored] == [both.id]
    assert [h["asset_id"] for h in scored[0]["hosts"]] == [first.id]
    assert client.get(endpoint, headers=auth_header, query_string={"cve_match": "no", "cvss_available": "yes"}).json["items"] == []
    unscored = client.get(endpoint, headers=auth_header, query_string={"cve_match": "yes", "cvss_available": "no"}).json["items"][0][
        "articles"
    ]
    assert [a["id"] for a in unscored] == [tagged.id]
    assert [h["asset_id"] for h in unscored[0]["hosts"]] == [first.id]
    zero = client.get(endpoint, headers=auth_header, query_string={"cvss_available": "yes", "cvss_min": 0, "cvss_max": 0}).json["items"][0][
        "articles"
    ]
    assert [a["id"] for a in zero] == [tagged.id]
    assert zero[0]["hosts"][0]["asset_id"] == second.id
    cve_only = client.get(endpoint, headers=auth_header, query_string={"cve_match": "yes", "package_match": "no"}).json["items"][0][
        "articles"
    ]
    assert [a["id"] for a in cve_only] == [tagged.id] and len(cve_only[0]["hosts"]) == 2
    product_only = client.get(endpoint, headers=auth_header, query_string={"cve_match": "no", "package_match": "yes"}).json["items"][0][
        "articles"
    ]
    assert {a["id"] for a in product_only} == {both.id, product.id}
    assert len(next(a for a in product_only if a["id"] == both.id)["hosts"]) == 1
    assert client.get(endpoint, headers=auth_header, query_string={"cve_match": "no", "package_match": "no"}).json["items"] == []

    packages = client.get(endpoint, headers=auth_header, query_string={"package": "BUILDkit", "cvss_min": 7, "cvss_max": 8.5}).json["items"][
        0
    ]["articles"]
    host = packages[0]["hosts"][0]
    assert host["max_cvss"] == 8.1 and len(host["software"]) == 1
    assert host["software"][0]["versions"] == ["v0.32.0", "v0.32.1"]
    assert {r["source"]["name"] for r in host["cve_matches"][0]["ratings"]} == {"NVD"}
    assert client.get(endpoint, headers=auth_header, query_string={"package": "buildkit", "cvss_min": 9}).json["items"] == []
    network = client.get(endpoint, headers=auth_header, query_string={"tag": " SBOMPROBER_NETWORK ", "cve_match": "yes"}).json
    assert network["filters"]["tag"] == "sbomprober_network"
    assert all(h["asset_id"] == first.id for story in network["items"] for a in story["articles"] for h in a["hosts"])
    assert client.get(endpoint, headers=auth_header, query_string={"tag": "sbomprober_network", "group_id": group.id}).json["items"] == []
    assert client.get(endpoint, headers=auth_header, query_string={"tag": "sbomprober_net"}).json["items"] == []
    for selection in ({"asset_id": second.id}, {"group_id": group.id}):
        selected = client.get(endpoint, headers=auth_header, query_string=selection).json["items"][0]["articles"]
        assert all([h["asset_id"] for h in a["hosts"]] == [second.id] for a in selected)
    for invalid in (
        {"cvss_min": -1},
        {"cvss_max": 11},
        {"cvss_min": "nan"},
        {"cvss_min": 8, "cvss_max": 7},
        {"cve_match": "invalid"},
        {"page": 0},
    ):
        assert client.get(endpoint, headers=auth_header, query_string=invalid).status_code == 400

    # Live changes affect both filters and summary counts without rescanning.
    client.put(first_base + "/sbom/cves/CVE-2026-12345", headers=auth_header, json={"enabled": False})
    assert client.get(endpoint, headers=auth_header, query_string={"cvss_min": 7}).json["items"] == []
    product.title = "Unrelated announcement"
    db.session.commit()
    remaining = client.get(endpoint, headers=auth_header).json["items"][0]["articles"]
    assert product.id not in {a["id"] for a in remaining}

    # Neither the asset catalog nor matching results disclose other organizations.
    organization = Organization(name="Private overview organization")
    db.session.add(organization)
    group.organization = organization
    db.session.commit()
    data = client.get(endpoint, headers=auth_header).json
    assert second.id not in {a["id"] for a in data["assets"]}
    assert group.id not in {g["id"] for g in data["groups"]}
    assert "private-host" not in data["tags"]
    assert "private-host" not in client.get("/api/assets/tags", headers=auth_header).json["tags"]
    assert client.get(endpoint, headers=auth_header, query_string={"asset_id": second.id}).json["items"] == []
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS"]) if p not in role.permissions)
    acl = grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
    tagged.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    assert client.get(endpoint, headers=auth_header_user_permissions, query_string={"cve_match": "yes"}).json["items"] == []
    acl.item_id = "unavailable"
    db.session.commit()
    assert client.get(endpoint, headers=auth_header_user_permissions).json["items"] == []


def test_asset_tag_updates_filters_and_access(client, auth_header, session):
    group = AssetGroup("Tagged hosts", "", User.find_by_name("admin").organization)
    private_org = Organization(name="Private tag organization")
    db.session.add_all([group, private_org])
    db.session.flush()
    private_group = AssetGroup("Private tags", "", private_org)
    db.session.add(private_group)
    db.session.commit()
    ids = []
    for name in ("Tag host A", "Tag host B"):
        response = client.post(
            "/api/assets",
            headers=auth_header,
            json={"name": name, "serial": "", "description": "", "group": group.id, "tags": [" Fleet ", "fleet", "network", ""]},
        )
        assert response.status_code == 201, response.json
        ids.append(response.json["id"])
    private_asset = Asset("Private tag host", "", "", group=private_group, tags=["secret-tag", "fleet"])
    db.session.add(private_asset)
    db.session.commit()
    catalog = client.get("/api/assets/tags", headers=auth_header).json["tags"]
    assert "fleet" in catalog and "network" in catalog and "secret-tag" not in catalog
    first = f"/api/assets/{ids[0]}"
    assert client.put(first, headers=auth_header, json={"name": "Renamed tag host"}).status_code == 201
    assert client.get(first, headers=auth_header).json["tags"] == ["fleet", "network"]
    assert client.put(first, headers=auth_header, json={"tags": ["network", " NETWORK ", "fleet"]}).status_code == 201
    for page in (1, 2):
        result = client.get(
            "/api/assets",
            headers=auth_header,
            query_string={"tag": " FLEET ", "group": group.id, "limit": 1, "page": page, "order": "name_asc"},
        ).json
        assert result["total_count"] == 2 and len(result["items"]) == 1
        assert result["items"][0]["id"] == ids[page - 1]
    assert client.get("/api/assets", headers=auth_header, query_string={"tag": "flee"}).json["items"] == []
    assert client.get("/api/assets", headers=auth_header, query_string={"tag": "fleet", "search": "no-such-host"}).json["items"] == []
    for invalid in ("fleet", [1], None):
        assert client.put(first, headers=auth_header, json={"tags": invalid}).status_code == 400
    assert client.put(f"/api/assets/{private_asset.id}", headers=auth_header, json={"tags": ["network"]}).status_code == 403
    assert client.put(first, headers=auth_header, json={"tags": []}).status_code == 201
    assert client.get(first, headers=auth_header).json["tags"] == []
    assert client.delete(first, headers=auth_header).status_code == 200
    assert not db.session.scalar(db.select(AssetTag).filter_by(asset_id=ids[0]))


def test_sbom_preparation_is_private_and_requires_complete_worker_batches(
    client, auth_header, auth_header_user_permissions, api_header, session
):
    # Materialize SQLite's outer transaction before savepoints, so commits remain isolated.
    session.connection().exec_driver_sql("BEGIN")
    session().join_transaction_mode = "create_savepoint"
    response = client.post(
        "/api/assets/sbom-imports",
        headers={"Authorization": auth_header["Authorization"]},
        data={"file": (io.BytesIO(FIXTURE.read_bytes()), "async.cdx.json")},
    )
    assert response.status_code == 202
    upload_id = response.json["id"]
    progress_url = f"/api/assets/sbom-uploads/{upload_id}"
    worker_url = f"/api/worker/sbom-uploads/{upload_id}"
    assert response.json["status"] == "QUEUED" and response.json["import_id"] is None
    other_user = User.find_by_name("user")
    other_user.roles = list(User.find_by_name("admin").roles)
    db.session.commit()
    assert client.get(progress_url, headers=auth_header_user_permissions).status_code == 404
    assert client.get(worker_url, headers=auth_header).status_code == 401
    source = client.get(worker_url, headers=api_header)
    assert source.status_code == 200, source.json
    assert source.data == FIXTURE.read_bytes()
    parsed = parse_sbom(source.data)
    begin = client.post(worker_url + "/begin", headers=api_header, json=parsed.summary.model_dump())
    preview_url = f"/api/assets/sbom-imports/{begin.json['import_id']}"
    assert client.get(preview_url, headers=auth_header).status_code == 409
    assert client.post(preview_url, headers=auth_header, json={"name": "Partial", "asset_group_id": "default"}).status_code == 409
    assert client.post(worker_url + "/complete", headers=api_header, json={}).status_code == 409
    batch = {"offset": 0, "items": [c.model_dump() for c in parsed.components]}
    assert client.post(worker_url + "/components", headers=api_header, json=batch).status_code == 200
    assert client.post(worker_url + "/components", headers=api_header, json=batch).status_code == 200
    ready = client.post(worker_url + "/complete", headers=api_header, json={})
    assert ready.json["status"] == "READY"
    assert client.get(progress_url, headers=auth_header).json["status"] == "READY"
    assert client.get(preview_url, headers=auth_header).json["summary"]["component_count"] == 3
    assert db.session.get(AssetSbomUpload, upload_id).source is None
    assert not db.session.scalar(db.select(AssetSbomUploadReference).filter_by(upload_id=upload_id))
    assert client.get(worker_url, headers=api_header).status_code == 409


def test_sbom_preparation_failure_discards_partial_preview_and_allows_retry(client, auth_header, api_header, session, monkeypatch):
    # Materialize SQLite's outer transaction before savepoints, so commits remain isolated.
    session.connection().exec_driver_sql("BEGIN")
    session().join_transaction_mode = "create_savepoint"

    def stage():
        return client.post(
            "/api/assets/sbom-imports",
            headers={"Authorization": auth_header["Authorization"]},
            data={"file": (io.BytesIO(FIXTURE.read_bytes()), "retry.cdx.json")},
        )

    queued = stage()
    assert queued.status_code == 202
    upload_id = queued.json["id"]
    assert stage().json["id"] == upload_id
    endpoint = f"/api/worker/sbom-uploads/{upload_id}"
    parsed = parse_sbom(FIXTURE.read_bytes())
    started = client.post(endpoint + "/begin", headers=api_header, json=parsed.summary.model_dump())
    import_id = started.json["import_id"]
    assert (
        client.post(
            endpoint + "/components", headers=api_header, json={"offset": 0, "items": [parsed.components[0].model_dump()]}
        ).status_code
        == 200
    )
    failed = client.post(endpoint + "/failure", headers=api_header, json={})
    assert failed.json["status"] == "FAILED"
    assert db.session.get(AssetSbomUpload, upload_id).source is None
    assert db.session.get(AssetSbomImport, import_id) is None
    assert not db.session.scalar(db.select(AssetSbomUploadReference).filter_by(upload_id=upload_id))
    assert client.post(endpoint + "/complete", headers=api_header, json={}).status_code == 409
    retry_id = stage().json["id"]
    assert retry_id != upload_id
    retry = db.session.get(AssetSbomUpload, retry_id)
    retry.updated -= timedelta(days=2)
    db.session.commit()
    from core.service.task import TaskService

    TaskService.cleanup_history()
    assert db.session.get(AssetSbomUpload, retry_id).status == "FAILED"
    assert db.session.get(AssetSbomUpload, retry_id).source is None

    with monkeypatch.context() as patch:
        patch.setattr(queue_manager.queue_manager, "enqueue_task", lambda *args, **kwargs: False)
        assert stage().status_code == 503
    assert not db.session.scalar(db.select(AssetSbomUpload.id).where(AssetSbomUpload.source.is_not(None)))


def test_sbom_worker_rechecks_importer_permission(client, auth_header, api_header, session):
    # Materialize SQLite's outer transaction before savepoints, so commits remain isolated.
    session.connection().exec_driver_sql("BEGIN")
    session().join_transaction_mode = "create_savepoint"
    response = client.post(
        "/api/assets/sbom-imports",
        headers={"Authorization": auth_header["Authorization"]},
        data={"file": (io.BytesIO(FIXTURE.read_bytes()), "revoked.cdx.json")},
    )
    assert response.status_code == 202
    upload_id = response.json["id"]
    owner = User.find_by_name("admin")
    owner.roles = []
    db.session.commit()
    assert client.get(f"/api/worker/sbom-uploads/{upload_id}", headers=api_header).status_code == 404
    upload = db.session.get(AssetSbomUpload, upload_id)
    assert upload.status == "FAILED" and upload.source is None and upload.import_id is None
