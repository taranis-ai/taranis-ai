from types import SimpleNamespace

from fakeredis import FakeRedis
from loro import ExportMode, LoroDoc, VersionVector

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
