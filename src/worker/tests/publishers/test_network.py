import pytest

from worker.publishers import network


@pytest.mark.parametrize(
    ("configured", "job_timeout", "expected"),
    [(30, 40, 20), (12, 40, 12), (30, -1, 30), (30, None, 30)],
)
def test_effective_network_timeout(monkeypatch, mock_job, configured, job_timeout, expected):
    mock_job.timeout = job_timeout
    monkeypatch.setattr(network, "get_current_job", lambda: mock_job if job_timeout is not None else None)

    assert network.effective_network_timeout({"NETWORK_TIMEOUT": configured}) == expected
