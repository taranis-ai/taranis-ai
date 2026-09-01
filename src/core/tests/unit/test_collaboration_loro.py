from types import SimpleNamespace

from fakeredis import FakeRedis
from loro import ExportMode, LoroDoc, VersionVector

from core.api.collaboration import _peer_results, _valid_id
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
