import pytest
import sys
import os
from pathlib import Path
from prefect.testing.utilities import prefect_test_harness

# Add actual paths for imports based on file location
current_dir = Path(__file__).parent
worker_path = current_dir.parent.parent
src_path = worker_path.parent.parent / "src"

# Add paths to sys.path if not already present
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set testing environment variables
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DEBUG", "1")


@pytest.fixture(scope="function")
def prefect_e2e_environment():
    """Setup Prefect test environment for E2E tests"""
    with prefect_test_harness():
        yield


@pytest.fixture(scope="session")
def e2e_test_data():
    """Shared test data for E2E tests"""
    return {
        "test_product_id": " TODO",
        "test_publisher_id": " TODO",
        "test_connector_id": "TODO",
        "test_source_id": "TODO",
        "test_bot_id": 42
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment for all E2E tests"""
    # Ensure we have the right working directory
    original_cwd = os.getcwd()
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    yield
    
    # Restore original working directory
    os.chdir(original_cwd)


def pytest_configure(config):
    """Configure pytest for E2E tests"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests that test complete workflows"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 5 seconds"
    )
    config.addinivalue_line(
        "markers", "prefect: Tests that use Prefect functionality"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for E2E tests"""
    # Automatically mark all tests in e2e directory
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.prefect)


def pytest_sessionstart(session):
    """Called after the Session object has been created"""
    print("\nStarting E2E test session for Prefect migration")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished"""
    if exitstatus == 0:
        print("E2E test session completed successfully")
    else:
        print("E2E test session completed with failures")