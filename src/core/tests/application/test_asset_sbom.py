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
from core.model.asset_intelligence import AssetArticleMatch, AssetMatchRun, AssetTrigger, SoftwareMatchRule
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


def matched_stories(client, headers, base, **filters):
    asset_id = base.rsplit("/", 1)[1]
    query = {"asset_id": asset_id, **filters}
    response = client.get("/api/assess/stories", headers=headers, query_string=query)
    assert response.status_code == 200, response.json
    stories = response.json["items"]
    for story in stories:
        evidence = client.get(f"/api/assess/stories/{story['id']}/asset-matches", headers=headers, query_string=query)
        assert evidence.status_code == 200, evidence.json
        story["articles"] = [article["hosts"][0] for article in evidence.json["articles"]]
    return stories


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
    assert (
        client.get("/api/assess/stories", query_string={"asset_id": created.json["id"]}, headers=auth_header_user_permissions).status_code
        == 403
    )


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
    assert matched_stories(client, auth_header, base) == []

    selected = [requests["id"], *[t["id"] for t in openssl]]
    scan = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert scan["status"] == "QUEUED" and scan["days"] == 30
    batch_url = f"/api/worker/asset-match-runs/{scan['id']}/batch"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "COMPLETED"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "COMPLETED"
    matches = matched_stories(client, auth_header, base)
    assert len(matches) == 1
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
    assert len(matched_stories(client, auth_header, base)) == 1
    corrected = unrelated | {"title": original["title"], "content": "<p>Python REQUESTS uses TLS.</p>"}
    assert client.post("/api/worker/news-items", headers=api_header, json=[corrected]).status_code == 200
    assert len(matched_stories(client, auth_header, base)) == 2
    Story.group_stories([NewsItem.get(original["id"]).story_id, NewsItem.get(unrelated["id"]).story_id])
    grouped = matched_stories(client, auth_header, base)
    assert len(grouped) == 1
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
    grouped = matched_stories(client, auth_header, base)
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
    remaining = matched_stories(client, auth_header, base)[0]
    for article in remaining["articles"]:
        assert len(article["software"]) == 3
        assert openssl[0]["component_id"] not in {c["id"] for p in article["software"] for c in p["components"]}
        assert openssl[0]["id"] not in {t["id"] for e in article["evidence"] for r in e["matches"] for t in r["triggers"]}
    assert client.post(base + "/triggers/suggestions", headers=auth_header, json={}).json["added"] == 0
    saved = client.get(base + "/triggers", headers=auth_header).json["items"]
    assert next(t for t in saved if t["id"] == openssl[0]["id"])["phrase"] == "SSL library"
    assert client.post(base + "/triggers/selection", headers=auth_header, json={"trigger_ids": selected, "enabled": False}).status_code == 200
    assert matched_stories(client, auth_header, base) == []


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
    query = {"asset_id": asset_id, "asset_cve_match": "yes" if cve_only else "any", "sort": "date_desc"}
    ordinary = client.get("/api/assess/stories", headers=auth_header, query_string={"source": source.id, "limit": 400}).json["items"]
    expected_ids = [story["id"] for story in ordinary if story["id"] in expected_ids]
    first = client.get("/api/assess/stories", headers=auth_header, query_string=query).json
    second = client.get("/api/assess/stories", headers=auth_header, query_string={**query, "page": 1}).json
    assert [story["id"] for story in first["items"]] == expected_ids[:20]
    assert [story["id"] for story in second["items"]] == expected_ids[20:]
    assert first["counts"]["total_count"] == second["counts"]["total_count"] == 21
    small_page = client.get("/api/assess/stories", headers=auth_header, query_string={**query, "limit": 5, "page": 1}).json
    assert [story["id"] for story in small_page["items"]] == expected_ids[5:10]
    empty = client.get("/api/assess/stories", headers=auth_header, query_string={**query, "page": 2}).json
    assert empty["items"] == []
    grouped_id = NewsItem.get(articles[0]["id"]).story_id
    grouped_story = next(story for story in first["items"] + second["items"] if story["id"] == grouped_id)
    assert grouped_story["matched_assets"][0]["cve_count"] == 1
    evidence = client.get(f"/api/assess/stories/{grouped_id}/asset-matches", headers=auth_header, query_string=query).json
    assert len(evidence["articles"]) == 2
    for article in evidence["articles"]:
        host = article["hosts"][0]
        assert len(host["software"]) == 2 and len(host["evidence"]) == 1
        assert len(host["evidence"][0]["matches"]) == 2

    if cve_only:
        triggers = client.get(f"/api/assets/{asset_id}/triggers", headers=auth_header).json["items"]
        client.post(
            f"/api/assets/{asset_id}/triggers/selection",
            headers=auth_header,
            json={"trigger_ids": [trigger["id"] for trigger in triggers], "enabled": False},
        )
    unmatched = create_story(news_items=[build_news_item_payload(source.id, title="Unrelated local announcement")])
    matched = Story.get(expected_ids[0])
    matched.read, matched.important = True, True
    db.session.commit()
    assess_query = {"source": source.id, "sort": "date_asc", "limit": 400}
    ordinary = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query).json["items"]
    expected_assess = [story["id"] for story in ordinary if story["id"] in expected_ids]
    assert unmatched.id in {story["id"] for story in ordinary}
    assert all("matched_assets" not in story for story in ordinary)
    assess_query.update(asset_match="true", limit=5)
    first = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query).json
    second = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query | {"page": 1}).json
    assert [story["id"] for story in first["items"]] == expected_assess[:5]
    assert [story["id"] for story in second["items"]] == expected_assess[5:10]
    assert first["counts"]["total_count"] == second["counts"]["total_count"] == 21
    assert first["counts"]["read_count"] == first["counts"]["important_count"] == 1
    expected_asset = {
        "id": asset_id,
        "name": "Paged intelligence",
        "max_cvss": None,
        "cve_count": 1,
        "software_match": not cve_only,
    }
    assert all(story["matched_assets"] == [expected_asset] for story in first["items"])
    unread = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query | {"read": "false"}).json
    assert unread["counts"]["total_count"] == 20 and unread["counts"]["read_count"] == 0
    no_count = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query | {"no_count": "true", "page": 1}).json
    assert "counts" not in no_count and [story["id"] for story in no_count["items"]] == expected_assess[5:10]
    client.delete(f"/api/assets/{asset_id}", headers=auth_header)
    empty = client.get("/api/assess/stories", headers=auth_header, query_string=assess_query).json
    assert empty["items"] == [] and empty["counts"]["total_count"] == 0


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
    visible_story = matched_stories(client, auth_header_user_permissions, base)[0]
    assert len(visible_story["articles"]) == 201
    assess_url = "/api/assess/stories?asset_match=true"
    assert client.get(assess_url, headers=auth_header_user_permissions).json["counts"]["total_count"] == 1
    acl.item_id = "unavailable"
    db.session.commit()
    assert matched_stories(client, auth_header_user_permissions, base) == []
    assert client.get(assess_url, headers=auth_header_user_permissions).json["items"] == []
    acl.item_id = source.id
    story.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    assert matched_stories(client, auth_header_user_permissions, base) == []
    assert client.get(assess_url, headers=auth_header_user_permissions).json["items"] == []
    story.upsert_attribute(NewsItemAttribute(key="TLP", value="clear"))
    story.news_items[0].upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    visible_story = matched_stories(client, auth_header_user_permissions, base)[0]
    assert len(visible_story["articles"]) == 200
    assert story.news_items[0].id not in {a["id"] for a in visible_story["articles"]}
    # A scan must recheck permissions when the worker runs, not only when it was queued.
    scan = client.post(base + "/match-runs", headers=auth_header_user_permissions, json={"days": 0})
    role.permissions = [p for p in role.permissions if p.code != "ASSESS_ACCESS"]
    db.session.commit()
    batch_url = f"/api/worker/asset-match-runs/{scan.json['id']}/batch"
    assert client.post(batch_url, headers=api_header, json={}).json["status"] == "FAILED"
    assert db.session.get(AssetMatchRun, scan.json["id"]).processed == 0
    assert (
        client.get("/api/assess/stories", query_string={"asset_id": base.rsplit("/", 1)[1]}, headers=auth_header_user_permissions).status_code
        == 403
    )
    if Permission.get("ASSESS_ACCESS") not in role.permissions:
        role.permissions.append(Permission.get("ASSESS_ACCESS"))
    role.permissions = [permission for permission in role.permissions if permission.code != "ASSETS_ACCESS"]
    db.session.commit()
    assert client.get(assess_url, headers=auth_header_user_permissions).status_code == 403
    assert client.get("/api/assess/stories?asset_match=false", headers=auth_header_user_permissions).status_code == 200


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


@pytest.mark.parametrize(("software_matching", "cve_matching"), [(True, False), (False, True), (False, False)])
def test_import_matching_choices(client, auth_header, api_header, session, finding_document, software_matching, cve_matching):
    source = create_osint_source(rank=0)
    story = create_story(news_items=[build_news_item_payload(source.id, title="BuildKit security bulletin")])
    story.news_items[0].tags.append(NewsItemTag("CVE-2026-12345", "CVE"))
    db.session.commit()
    preview = upload(client, auth_header, finding_document).json
    endpoint = f"/api/assets/sbom-imports/{preview['id']}"
    body = {
        "name": "Reviewed import",
        "asset_group_id": AssetGroup.get_default_group().id,
        "enable_software_matching": software_matching,
        "enable_cve_matching": cve_matching,
    }
    created = client.post(endpoint, headers=auth_header, json=body)
    assert created.status_code == 201, created.json
    base = f"/api/assets/{created.json['id']}"
    rules = client.get(base + "/triggers", headers=auth_header).json["items"]
    assert rules and any(rule["enabled"] for rule in rules) == software_matching
    inventory = client.get(base + "/sbom", headers=auth_header).json
    assert inventory["summary"]["component_count"] == preview["summary"]["component_count"]
    findings = client.get(base + "/cti", headers=auth_header).json["iocs"]
    cve = next(item for item in findings if item["value"] == "CVE-2026-12345")
    assert cve["findings"][0]["matching_enabled"] == cve_matching
    assert bool(cve["news_item_ids"]) == cve_matching
    assert cve["findings"][0]["records"] == finding_document["vulnerabilities"][:2]
    run = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert bool(run) == software_matching
    if run:
        assert client.post(f"/api/worker/asset-match-runs/{run['id']}/batch", headers=api_header, json={}).status_code == 200
    matches = matched_stories(client, auth_header, base)
    assert bool(matches) == (software_matching or cve_matching)
    if matches:
        article = matches[0]["articles"][0]
        assert bool(article["evidence"]) == software_matching
        assert bool(article["cve_matches"]) == cve_matching
    body.update(enable_software_matching=not software_matching, enable_cve_matching=not cve_matching)
    assert client.post(endpoint, headers=auth_header, json=body).status_code == 200
    assert client.get(base + "/triggers", headers=auth_header).json["items"] == rules
    assert client.get(base + "/cti", headers=auth_header).json["iocs"] == findings
    assert len(db.session.scalars(db.select(AssetMatchRun).filter_by(asset_id=created.json["id"])).all()) == int(software_matching)


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
    results = matched_stories(client, auth_header, base)
    assert len(results) == 1 and len(results[0]["articles"]) == 2
    assert all(len(a["cve_matches"]) == 1 and not a["evidence"] for a in results[0]["articles"])
    assess_url = "/api/assess/stories?asset_match=true"
    assert client.get(assess_url, headers=auth_header).json["counts"]["total_count"] == 1
    run = client.get(base + "/match-runs", headers=auth_header).json["run"]
    assert client.post(f"/api/worker/asset-match-runs/{run['id']}/batch", headers=api_header, json={}).status_code == 200
    results = matched_stories(client, auth_header, base)
    article = next(a for a in results[0]["articles"] if a["title"] == "BuildKit security bulletin")
    assert article["evidence"] and len(article["software"]) == 2 and len(article["cve_matches"]) == 1
    assert len(results[0]["articles"]) == 3
    results = matched_stories(client, auth_header, base, asset_cve_match="yes")
    assert len(results[0]["articles"]) == 2
    assert article in results[0]["articles"]
    triggers = client.get(base + "/triggers", headers=auth_header).json["items"]
    client.post(base + "/triggers/selection", headers=auth_header, json={"trigger_ids": [t["id"] for t in triggers], "enabled": False})
    assert len(matched_stories(client, auth_header, base)[0]["articles"]) == 2
    toggle = base + "/sbom/cves/CVE-2026-12345"
    assert client.put(toggle, headers=auth_header, json={"enabled": False}).status_code == 200
    assert matched_stories(client, auth_header, base) == []
    assert matched_stories(client, auth_header, base, asset_cve_match="yes") == []
    assert client.get(assess_url, headers=auth_header).json["items"] == []
    disabled = client.get(base + "/cti?search=12345", headers=auth_header).json["iocs"][0]
    assert not disabled["findings"][0]["matching_enabled"] and not disabled["news_item_ids"]
    client.put(toggle, headers=auth_header, json={"enabled": True})
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS"]) if p not in role.permissions)
    acl = grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
    db.session.commit()
    assert len(matched_stories(client, auth_header_user_permissions, base)) == 1
    assert client.get(assess_url, headers=auth_header_user_permissions).json["counts"]["total_count"] == 1
    story.news_items[0].upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    visible = client.get(base + "/cti?search=12345", headers=auth_header_user_permissions).json["iocs"][0]
    assert visible["news_item_ids"] == [story.news_items[1].id]
    articles = matched_stories(client, auth_header_user_permissions, base, asset_cve_match="yes")[0]["articles"]
    assert [article["id"] for article in articles] == [story.news_items[1].id]
    acl.item_id = "unavailable"
    db.session.commit()
    assert matched_stories(client, auth_header_user_permissions, base) == []
    assert matched_stories(client, auth_header_user_permissions, base, asset_cve_match="yes") == []
    assert not client.get(base + "/cti?search=12345", headers=auth_header_user_permissions).json["iocs"][0]["news_item_ids"]
    for item in story.news_items:
        for tag in item.tags:
            db.session.delete(tag)
    db.session.commit()
    assert matched_stories(client, auth_header, base) == []
    assert matched_stories(client, auth_header, base, asset_cve_match="yes") == []
    assert client.get(assess_url, headers=auth_header).json["items"] == []


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
    replacement["components"].append({"type": "library", "name": "new-software", "version": "1", "bom-ref": "new-software"})
    replacement["vulnerabilities"].append({"id": "CVE-2026-54321", "affects": [{"ref": "new-software"}]})
    new = upload(client, auth_header, replacement).json
    comparison = client.get(f"/api/assets/sbom-imports/{new['id']}?asset_id={asset.id}", headers=auth_header).json["comparison"]
    assert comparison["components_added"] == 2 and comparison["components_removed"] == 1
    assert comparison["cves_removed"] == 1 and comparison["expected_sha256"] == preview["sha256"]
    body = {"import_id": new["id"], "expected_sha256": "stale", "enable_software_matching": False, "enable_cve_matching": False}
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 409
    assert client.get(base + "/sbom", headers=auth_header).json["id"] == preview["id"]
    body["expected_sha256"] = preview["sha256"]
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 200
    body.update(enable_software_matching=True, enable_cve_matching=True)
    assert client.put(base + "/sbom", headers=auth_header, json=body).status_code == 200
    new_rules = client.get(base + "/triggers?search=new-software", headers=auth_header).json["items"]
    assert new_rules and not any(rule["enabled"] for rule in new_rules)
    new_cve = client.get(base + "/cti?search=54321", headers=auth_header).json["iocs"][0]
    assert not new_cve["findings"][0]["matching_enabled"]
    retained_rules = client.get(base + "/triggers?search=internal-agent", headers=auth_header).json["items"]
    assert any(rule["enabled"] for rule in retained_rules)
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
    versions = db.session.scalars(db.select(AssetTrigger).join(SoftwareMatchRule).where(SoftwareMatchRule.phrase == "BuildKit")).all()
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


def test_assess_asset_filters_and_evidence_preserve_host_scope_and_scores(
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

    endpoint = "/api/assess/stories"
    evidence_url = f"{endpoint}/{story.id}/asset-matches"
    assessed = client.get(endpoint, headers=auth_header, query_string={"asset_match": "true"}).json
    assert assessed["counts"]["total_count"] == 1
    first_summary = {"id": first.id, "name": "Host A", "max_cvss": 9.1, "cve_count": 2, "software_match": True}
    second_summary = {"id": second.id, "name": "Host B", "max_cvss": 0, "cve_count": 1, "software_match": True}
    assert assessed["items"][0]["matched_assets"] == [first_summary, second_summary]
    data = client.get(evidence_url, headers=auth_header).json
    articles = {a["id"]: a for a in data["articles"]}
    assert set(articles) == {both.id, tagged.id, product.id}
    hosts = articles[both.id]["hosts"]
    assert [(h["asset_name"], h["max_cvss"], h["software_match"]) for h in hosts] == [("Host A", 9.1, True), ("Host B", None, True)]
    ratings = hosts[0]["cve_matches"][0]["ratings"]
    assert {r["source"]["name"] for r in ratings} == {"NVD", "Vendor advisory"}
    assert {r["method"] for r in ratings} == {"CVSSv2", "CVSSv31"}
    cases = [
        ({"asset_cvss_min": 7}, {both.id: [first.id]}),
        ({"asset_cvss_min": 0, "asset_cvss_max": 0}, {tagged.id: [second.id]}),
        ({"asset_cve_match": "yes", "asset_software_match": "no"}, {tagged.id: [first.id, second.id]}),
        ({"asset_cve_match": "no", "asset_software_match": "yes"}, {both.id: [second.id], product.id: [first.id, second.id]}),
        ({"asset_cve_match": "no", "asset_software_match": "no"}, {}),
        ({"asset_cve_match": "no", "asset_cvss_min": 0}, {}),
        ({"asset_tag": " SBOMPROBER_NETWORK ", "asset_cve_match": "yes"}, {both.id: [first.id], tagged.id: [first.id]}),
        ({"asset_tag": "sbomprober_network", "asset_group_id": group.id}, {}),
        ({"asset_tag": "sbomprober_net"}, {}),
        ({"asset_id": second.id, "asset_cve_match": "yes"}, {tagged.id: [second.id]}),
        ({"asset_group_id": group.id, "asset_cve_match": "yes"}, {tagged.id: [second.id]}),
    ]
    for filters, expected in cases:
        evidence = client.get(evidence_url, headers=auth_header, query_string=filters).json
        assert {a["id"]: [h["asset_id"] for h in a["hosts"]] for a in evidence["articles"]} == expected
        listed = client.get(endpoint, headers=auth_header, query_string={"asset_match": "true", **filters}).json
        assert listed["counts"]["total_count"] == int(bool(expected))
        if expected:
            assert {a["id"] for a in listed["items"][0]["matched_assets"]} == {host for hosts in expected.values() for host in hosts}
    for invalid in (
        {"asset_cvss_min": -1},
        {"asset_cvss_max": 11},
        {"asset_cvss_min": "nan"},
        {"asset_cvss_min": 8, "asset_cvss_max": 7},
        {"asset_cve_match": "invalid"},
    ):
        assert client.get(endpoint, headers=auth_header, query_string=invalid).status_code == 400
        assert client.get(evidence_url, headers=auth_header, query_string=invalid).status_code == 400

    # Several CVEs can be covered by separate articles, but must all belong to one asset.
    cve_filters = {"asset_match": "true", "tags": ["cve-2026-12345", "CVE-2026-12346"]}
    listed = client.get(endpoint, headers=auth_header, query_string=cve_filters).json
    assert listed["items"][0]["matched_assets"] == [first_summary]
    evidence = client.get(evidence_url, headers=auth_header, query_string=cve_filters).json
    assert {a["id"] for a in evidence["articles"]} == {both.id, tagged.id}
    assert all([h["asset_id"] for h in a["hosts"]] == [first.id] for a in evidence["articles"])
    assert client.get(endpoint, headers=auth_header, query_string={**cve_filters, "asset_cvss_min": 7}).json["items"] == []
    assert client.get(endpoint, headers=auth_header, query_string={"asset_match": "true", "tags": "CVE-2026-1234"}).json["items"] == []
    selected = client.get(evidence_url, headers=auth_header, query_string={"tags": "CVE-2026-12346"}).json
    assert len(selected["articles"]) == 1
    assert [h["max_cvss"] for h in selected["articles"][0]["hosts"]] == [None, 0]
    selected_stories = client.get(endpoint, headers=auth_header, query_string={"asset_match": "true", "tags": "CVE-2026-12346"}).json
    assert selected_stories["items"][0]["matched_assets"] == [
        first_summary | {"max_cvss": None, "cve_count": 1, "software_match": False},
        second_summary | {"software_match": False},
    ]

    client.put(first_base + "/sbom/cves/CVE-2026-12346", headers=auth_header, json={"enabled": False})
    assert client.get(endpoint, headers=auth_header, query_string=cve_filters).json["items"] == []
    client.put(first_base + "/sbom/cves/CVE-2026-12346", headers=auth_header, json={"enabled": True})
    client.put(first_base + "/sbom/cves/CVE-2026-12345", headers=auth_header, json={"enabled": False})
    assert client.get(endpoint, headers=auth_header, query_string={"asset_cvss_min": 7}).json["items"] == []
    product.title = "Unrelated announcement"
    db.session.commit()
    assert product.id not in {a["id"] for a in client.get(evidence_url, headers=auth_header).json["articles"]}

    organization = Organization(name="Private asset organization")
    db.session.add(organization)
    group.organization = organization
    db.session.commit()
    catalog = client.get("/api/assess/asset-filter-lists", headers=auth_header).json
    assert second.id not in {a["id"] for a in catalog["assets"]}
    assert group.id not in {g["id"] for g in catalog["groups"]}
    assert "private-host" not in catalog["tags"]
    assert client.get(endpoint, headers=auth_header, query_string={"asset_id": second.id}).json["items"] == []
    assert client.get(evidence_url, headers=auth_header, query_string={"asset_id": second.id}).json["articles"] == []
    assert client.get("/api/assess/asset-filter-lists", headers=auth_header_user_permissions).status_code == 403
    assert client.get(evidence_url, headers=auth_header_user_permissions).status_code == 403
    role = Role.filter_by_name("User")
    role.tlp_level = TLPLevel.CLEAR
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS"]) if p not in role.permissions)
    acl = grant_acl(role, ItemType.OSINT_SOURCE, source.id, read_only=True)
    tagged.upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    db.session.commit()
    assert client.get(endpoint, headers=auth_header_user_permissions, query_string={"asset_cve_match": "yes"}).json["items"] == []
    assert client.get(evidence_url, headers=auth_header_user_permissions, query_string={"asset_cve_match": "yes"}).json["articles"] == []
    acl.item_id = "unavailable"
    db.session.commit()
    assert client.get(endpoint, headers=auth_header_user_permissions, query_string={"asset_match": "true"}).json["counts"]["total_count"] == 0
    assert client.get(evidence_url, headers=auth_header_user_permissions).status_code == 404


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


def test_software_rules_are_shared_within_organization_but_enablement_stays_local(
    client, auth_header, auth_header_user_permissions, api_header, session, finding_document
):
    _, first_base = import_findings(client, auth_header, finding_document)
    finding_document["version"] = 2
    preview = upload(client, auth_header, finding_document).json
    second_id = client.post(
        f"/api/assets/sbom-imports/{preview['id']}",
        headers=auth_header,
        json={"name": "Disabled host", "asset_group_id": AssetGroup.get_default_group().id, "enable_software_matching": False},
    ).json["id"]
    second_base = f"/api/assets/{second_id}"
    first_rule = next(t for t in client.get(first_base + "/triggers", headers=auth_header).json["items"] if t["phrase"] == "buildkit")
    changed = client.put(
        first_base + f"/triggers/{first_rule['id']}",
        headers=auth_header,
        json={"phrase": "BuildKit engine", "context": ["security"], "enabled": True},
    )
    assert changed.status_code == 200
    second_rule = next(
        t for t in client.get(second_base + "/triggers", headers=auth_header).json["items"] if t["rule_id"] == first_rule["rule_id"]
    )
    assert second_rule["phrase"] == "BuildKit engine" and second_rule["context"] == ["security"]
    assert not second_rule["enabled"]
    alias = client.post(
        first_base + "/triggers",
        headers=auth_header,
        json={"component_id": first_rule["component_id"], "phrase": "Moby builder", "context": [], "enabled": True},
    ).json
    second_alias = next(
        t for t in client.get(second_base + "/triggers", headers=auth_header).json["items"] if t["rule_id"] == alias["rule_id"]
    )
    assert not second_alias["enabled"]
    finding_document["version"] = 3
    _, third_base = import_findings(client, auth_header, finding_document)
    third_rules = client.get(third_base + "/triggers", headers=auth_header).json["items"]
    assert any(t["rule_id"] == first_rule["rule_id"] and t["context"] == ["security"] and t["enabled"] for t in third_rules)
    assert any(t["rule_id"] == alias["rule_id"] and t["enabled"] for t in third_rules)
    source = create_osint_source(rank=0)
    payload = build_news_item_payload(source.id, title="BuildKit engine security bulletin")
    client.post("/api/worker/news-items", headers=api_header, json=[payload])
    assert matched_stories(client, auth_header, first_base) and matched_stories(client, auth_header, third_base)
    assert matched_stories(client, auth_header, second_base) == []
    client.put(
        first_base + f"/triggers/{first_rule['id']}",
        headers=auth_header,
        json={"phrase": "BuildKit engine", "context": ["critical"], "enabled": True},
    )
    assert matched_stories(client, auth_header, first_base) == matched_stories(client, auth_header, third_base) == []

    organization = Organization(name="Independent rule owners")
    db.session.add(organization)
    user = User.find_by_name("user")
    user.organization = organization
    role = Role.filter_by_name("User")
    role.permissions.extend(p for p in Permission.get_bulk(["ASSETS_ACCESS", "ASSETS_CREATE"]) if p not in role.permissions)
    db.session.commit()
    finding_document["version"] = 4
    _, private_base = import_findings(client, auth_header_user_permissions, finding_document)
    private_rule = next(
        t for t in client.get(private_base + "/triggers", headers=auth_header_user_permissions).json["items"] if t["phrase"] == "buildkit"
    )
    assert private_rule["rule_id"] != first_rule["rule_id"] and private_rule["context"] == []
    assert (
        client.put(
            first_base + f"/triggers/{first_rule['id']}",
            headers=auth_header_user_permissions,
            json={"phrase": "Unrelated", "context": [], "enabled": True},
        ).status_code
        == 403
    )
    assert client.delete(first_base, headers=auth_header).status_code == 200
    assert any(t["rule_id"] == first_rule["rule_id"] for t in client.get(third_base + "/triggers", headers=auth_header).json["items"])
