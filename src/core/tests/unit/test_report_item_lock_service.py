from core.managers.report_item_lock_service import ReportItemLockService


def test_report_lock_publication_runs_outside_state_lock(monkeypatch):
    service = ReportItemLockService()

    def assert_state_lock_is_available(*_args):
        assert service._lock.acquire(blocking=False)
        service._lock.release()

    monkeypatch.setattr(
        "core.managers.report_item_lock_service.realtime_publisher.report_lock_changed",
        assert_state_lock_is_available,
    )

    service.lock("report-item-1", "user-1", "organization-1")
    service.unlock("report-item-1", "organization-1")
