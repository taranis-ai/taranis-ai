"""
Fixtures for Prefect E2E tests

Assumes Docker Compose is already running.
Provides API client and test data for Prefect flow testing.
"""

import pytest
import time
from .utils.api_client import TaranisAPIClient, TestData, create_test_data, wait_for_flow_completion


@pytest.fixture(scope="session")
def api_client() -> TaranisAPIClient:
    """
    Authenticated API client for the test session.
    Assumes Docker Compose stack is already running.
    """
    # Give services a moment to fully start up
    print("Waiting for services to be ready...")
    time.sleep(10)

    client = TaranisAPIClient()

    # Authenticate with default admin credentials
    client.authenticate("admin", "admin")

    # Basic health check
    try:
        health = client.check_health()
        print(f"API health check passed: {health.get('version', 'unknown')}")
    except Exception as e:
        pytest.fail(f"API health check failed: {e}")

    # Check Prefect flows are available
    try:
        flows = client.check_prefect_flows()
        flow_names = [f.get("name") for f in flows.get("flows", [])]
        print(f"Available Prefect flows: {flow_names}")
    except Exception as e:
        print(f"Warning: Could not check Prefect flows: {e}")

    return client


@pytest.fixture(scope="class")
def test_data(api_client: TaranisAPIClient) -> TestData:
    """
    Create fresh test data for each test class.
    Creates products, presenters, publishers, connectors, bots, and news items.
    """
    print("Creating test data for test class...")

    try:
        data = create_test_data(api_client)
        print(f"Test data ready: {data}")
        yield data
    except Exception as e:
        pytest.fail(f"Failed to create test data: {e}")
    finally:
        # Test data cleanup could go here if needed
        print("Test data cleanup completed")


@pytest.fixture
def flow_runner(api_client: TaranisAPIClient):
    """Utility fixture for running and waiting for flows"""

    def run_and_wait(flow_type: str, timeout: int = 120, **params) -> str:
        """Run a flow and wait for completion"""
        if flow_type == "presenter":
            flow_run_id = api_client.trigger_presenter_flow(**params)
        elif flow_type == "publisher":
            flow_run_id = api_client.trigger_publisher_flow(**params)
        elif flow_type == "connector":
            flow_run_id = api_client.trigger_connector_flow(**params)
        elif flow_type == "bot":
            flow_run_id = api_client.trigger_bot_flow(**params)
        else:
            raise ValueError(f"Unknown flow type: {flow_type}")

        wait_for_flow_completion(api_client, flow_run_id, timeout)
        return flow_run_id

    return run_and_wait


# Test markers for organizing tests
def pytest_configure(config):
    """Register custom pytest markers for Prefect tests"""
    config.addinivalue_line("markers", "prefect: Prefect flow tests")
    config.addinivalue_line("markers", "presenter_flow: Presenter workflow tests")
    config.addinivalue_line("markers", "publisher_flow: Publisher workflow tests")
    config.addinivalue_line("markers", "connector_flow: Connector workflow tests")
    config.addinivalue_line("markers", "bot_flow: Bot workflow tests")
    config.addinivalue_line("markers", "slow: Slow running tests (flows)")
