from types import SimpleNamespace

from fakeredis import FakeRedis
from loro import ExportMode, LoroDoc, VersionVector

from core.api.collaboration import _authorized_document, _peer_results, _project_report_document, _report_document_config, _valid_id
from core.service.collaboration_loro import CollaborationStore


def test_duplicate_and_out_of_order_updates_converge():
    first = LoroDoc()
    first.get_text("title").insert(0, "alpha")
    first.commit()
    second = first.fork()
    second.get_text("title").insert(5, " bravo")
    second.commit()
    base = SimpleNamespace(
        id="document", snapshot=first.export(ExportMode.Snapshot()), version_vector=first.oplog_vv.encode(), stream_high_water_id="0-0"
    )
    store = CollaborationStore(FakeRedis())
    update = second.export(ExportMode.Updates(first.oplog_vv))

    store.accept(base, update, "second")
    store.accept(base, update, "second-duplicate")

    restored = store.load(base).document
    assert restored.get_text("title").to_string() == "alpha bravo"
    assert restored.oplog_vv.includes_vv(VersionVector.decode(second.oplog_vv.encode()))


def test_peer_results_are_reduced_to_the_fixed_protocol():
    operation_id = "0190f7d8-2a7b-7c7c-8d1f-8d9a4c2f7a10"
    result = _peer_results(
        [
            {"operation_id": operation_id, "status": "applied", "metadata_version": 3, "unexpected": "ignored"},
            {"operation_id": "not-an-id", "status": "applied"},
            {"operation_id": operation_id, "status": "unknown"},
        ]
    )
    assert result == [{"operation_id": operation_id, "status": "applied", "metadata_version": 3}]
    assert _valid_id("<script>alert(1)</script>") is None


def test_story_document_requires_snapshot_membership(monkeypatch):
    channel = SimpleNamespace(
        status="open",
        story_snapshots=[{"id": "snapshot-id"}],
        member_ids=["member-id"],
    )
    monkeypatch.setattr("core.api.collaboration._channel", lambda _channel_id: channel)
    row = SimpleNamespace(channel_id="channel-id", resource_kind="story", resource_id="snapshot-id")

    assert _authorized_document(row, SimpleNamespace(id="member-id"))
    assert not _authorized_document(row, SimpleNamespace(id="other-id"))


def test_report_projection_hides_managed_assessment_id_and_projects_rich_text():
    assessment = SimpleNamespace(
        id="assessment", title="Assessment ID", value="", required=True, attribute_type=SimpleNamespace(name="STRING")
    )
    summary = SimpleNamespace(id="summary", title="Summary", value="", required=True, attribute_type=SimpleNamespace(name="TEXT"))
    findings = SimpleNamespace(id="findings", title="Findings", value="", required=True, attribute_type=SimpleNamespace(name="RICH_TEXT"))
    report = SimpleNamespace(id="report-id", title="Draft", attributes=[assessment, summary, findings])
    store = SimpleNamespace(
        text_values=lambda _document: {"title": "Final", "attribute:summary": "Summary text"},
        rich_text_value=lambda _document, _root: ("<p>Finding</p>", "Finding"),
    )

    roots, _, rich_roots = _report_document_config(report)
    assert "attribute:assessment" not in roots
    assert rich_roots == {"attribute:findings"}
    assert _project_report_document(store, SimpleNamespace(), report, SimpleNamespace(story_snapshots=[]))
    assert assessment.value == "report-id"
    assert summary.value == "Summary text"
    assert findings.value == "<p>Finding</p>"
