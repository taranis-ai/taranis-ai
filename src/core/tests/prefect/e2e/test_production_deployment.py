import os
import time
import subprocess
import requests
import pytest

pytestmark = pytest.mark.e2e

DEFAULT_COMPOSE = os.getenv("E2E_COMPOSE_FILE", "docker/compose-variations/compose.e2e.yml")
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8080")

def _compose(*args, timeout=600):
    return subprocess.run(
        ["docker", "compose", "-f", DEFAULT_COMPOSE, *args],
        capture_output=True, text=True, timeout=timeout,
    )

def _wait_ok(url: str, seconds: int = 180):
    """Poll URL until 2xx/401/404 (migration-dependent), else raise."""
    start = time.time()
    last_exc = None
    while time.time() - start < seconds:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                return r
        except Exception as e:
            last_exc = e
        time.sleep(3)
    raise AssertionError(f"Service not ready: {url}; last_exc={last_exc}")

class TestProductionDeploymentWithMigrations:
    """E2E test for production deployment using PR #502 infrastructure"""

    @pytest.mark.skipif(os.getenv("CI") != "true", reason="Production deployment only in CI")
    def test_production_deployment_with_migrations_check(self):
        if not os.path.exists(DEFAULT_COMPOSE):
            pytest.skip(f"PR #502 compose file not found: {DEFAULT_COMPOSE}")

        try:
            up = _compose("up", "-d", "--build", timeout=900)
            assert up.returncode == 0, f"compose up failed:\n{up.stderr}"

            # Core API up
            r = _wait_ok(f"{BASE_URL}/api/config/version", seconds=240)
            assert r.status_code == 200, f"Core API not responding: {r.status_code} {r.text}"

            # DB-backed endpoints 
            for endpoint in ["/api/config/osint-sources", "/api/config/word-lists", "/api/config/bots"]:
                r = _wait_ok(f"{BASE_URL}{endpoint}", seconds=180)
                assert r.status_code in (200, 401, 404), f"{endpoint} -> {r.status_code} {r.text}"

            # Frontend accessible
            r = _wait_ok(f"{BASE_URL}/", seconds=180)
            assert r.status_code == 200, f"Frontend not accessible: {r.status_code}"

            # Services healthy
            ps = _compose("ps", timeout=60)
            assert ps.returncode == 0, f"compose ps failed: {ps.stderr}"
            out = ps.stdout.lower()
            assert "unhealthy" not in out, f"Some services unhealthy:\n{ps.stdout}"
            assert "exited" not in out and "dead" not in out, f"Some services exited:\n{ps.stdout}"

        except subprocess.TimeoutExpired:
            pytest.fail("Production deployment timed out during startup")
        except requests.exceptions.RequestException as e:
            pytest.fail(f"HTTP check failed: {e}")
        finally:
            # capture logs before tearing down
            _compose("ps", timeout=60)
            _compose("logs", timeout=120)
            down = _compose("down", "-v", "--remove-orphans", timeout=180)
            if down.returncode != 0:
                print(f"[WARN] compose down issues:\n{down.stderr}")

    def test_prefect_enabled_in_deployment(self):
        """Sanity: QueueManager exposes Prefect methods (fast, no Docker)."""
        from core.managers.queue_manager import QueueManager
        from unittest.mock import MagicMock

        mock_app = MagicMock()
        mock_app.config = {
            "QUEUE_BROKER_HOST": "localhost",
            "QUEUE_BROKER_USER": "test",
            "QUEUE_BROKER_PASSWORD": "test",
        }
        qm = QueueManager(mock_app)

        for name in [
            "get_queue_status",
            "ping_workers",
            "collect_osint_source",
            "execute_bot_task",
            "generate_product",
            "publish_product",
        ]:
            assert hasattr(qm, name), f"Prefect migration incomplete: missing {name}"
