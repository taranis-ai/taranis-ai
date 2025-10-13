"""
Fixtures for Prefect E2E tests

Automatically starts Prefect Server, Taranis Core, and Prefect Worker.
Provides API client and test data for Prefect flow testing.
"""

import os,re, pytest, time, subprocess, requests, responses, contextlib
from dotenv import dotenv_values
from urllib.parse import urlparse

from .utils.api_client import TaranisAPIClient, TestData, create_test_data


def _wait_for_server_to_be_alive(url: str, timeout_seconds: int = 10):
    """
    Poll a URL until it responds successfully or timeout is reached.
    Copied from frontend/tests/playwright/conftest.py
    """
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)
    
    for _ in range(timeout_seconds):
        try:
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    
    # Final attempt - will raise exception if still failing
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return True


@pytest.fixture(scope="session")
def run_prefect_server():
    """
    Start Prefect server as a subprocess for E2E testing.
    Waits for server to be available at http://127.0.0.1:4200/api/health
    """
    process = None
    log_file = None
    
    try:
        # Get environment configuration
        env = os.environ.copy()
        
        # Set Prefect API URL
        prefect_server_url = env.get("PREFECT_API_URL", "http://127.0.0.1:4200/api")
        
        print("Starting Prefect Server for Testing")
        
        # Open log file for output (prevents pipe blocking)
        log_file = open("prefect_server.log", "w")
        
        # Start Prefect server
        process = subprocess.Popen(
            ["prefect", "server", "start"],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        
        # Wait for Prefect server to be alive
        print(f"Waiting for Prefect Server to be available at {prefect_server_url}/health")
        _wait_for_server_to_be_alive(f"{prefect_server_url}/health", timeout_seconds=30)
        
        yield
        
    except Exception as e:
        pytest.fail(f"Failed to start Prefect Server: {e}")
    finally:
        if process:
            print("Shutting down Prefect Server")
            process.terminate()
            process.wait()
        if log_file:
            log_file.close()


@pytest.fixture(scope="session")
def run_core():
    """
    Start Flask Core as a subprocess for E2E testing.
    Adapted from frontend/tests/playwright/conftest.py
    """
    process = None
    log_file = None
    
    try:
        # Get path to core directory
        core_path = os.path.abspath("../core")
        env = {}
        
        # Load environment from core's test .env file
        if config := dotenv_values(os.path.join(core_path, "tests", ".env")):
            config = {k: v for k, v in config.items() if v}
            env = config
            
        env |= os.environ.copy()
        env["PYTHONPATH"] = core_path
        env["PATH"] = f"{os.path.join(core_path, '.venv', 'bin')}:{env.get('PATH', '')}"
        
        taranis_core_port = env.get("TARANIS_CORE_PORT", "5000")
        taranis_core_start_timeout = int(env.get("TARANIS_CORE_START_TIMEOUT", 10))
        
        # Clean up existing database if it exists
        with contextlib.suppress(Exception):
            parsed_uri = urlparse(env.get("SQLALCHEMY_DATABASE_URI"))
            if parsed_uri.path and os.path.exists(parsed_uri.path):
                os.remove(parsed_uri.path)
        
        print(f"Starting Taranis Core on port {taranis_core_port}")
        
        # Open log file for output
        log_file = open("core.log", "w")
        
        # Start Flask Core
        process = subprocess.Popen(
            ["flask", "run", "--no-reload", "--port", taranis_core_port],
            cwd=core_path,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        
        core_url = env.get("TARANIS_CORE_URL", f"http://127.0.0.1:{taranis_core_port}/api")
        print(f"Waiting for Taranis Core to be available at: {core_url}/isalive")
        _wait_for_server_to_be_alive(f"{core_url}/isalive", taranis_core_start_timeout)
        
        yield
        
    except Exception as e:
        pytest.fail(f"Failed to start Taranis Core: {e}")
    finally:
        if process:
            print("Shutting down Taranis Core")
            process.terminate()
            process.wait()
        if log_file:
            log_file.close()


@pytest.fixture(scope="session")
def run_worker():
    """
    Start Prefect Worker as a subprocess for E2E testing.
    Worker imports all flows and waits for Prefect to execute them.
    """
    process = None
    log_file = None
    
    try:
        # Get environment configuration
        env = os.environ.copy()
        
        print("Starting Prefect Worker")
        
        # Open log file for output
        log_file = open("worker.log", "w")
        
        # Start worker process that imports all flows
        process = subprocess.Popen(
            ["python", "-m", "worker.start"],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        
        # Give worker a moment to start and import flows
        time.sleep(3)
        
        # Check if process is still running 
        if process.poll() is not None:
            raise Exception(f"Worker process exited immediately with code {process.returncode}")
        
        yield
        
    except Exception as e:
        pytest.fail(f"Failed to start Prefect Worker: {e}")
    finally:
        if process:
            print("Shutting down Prefect Worker")
            process.terminate()
            process.wait()
        if log_file:
            log_file.close()


@pytest.fixture(scope="session", autouse=True)
def _start_stack(run_prefect_server, run_core, run_worker):
    """
    Autouse fixture that ensures all services start in correct order.
    This runs automatically before any test.
    
    Order matters:
    1. Prefect Server (infrastructure)
    2. Core (application)  
    3. Worker (connects to both)
    """
    print("\n" + "="*60)
    print("E2E Test Stack Started Successfully")
    print("  ✓ Prefect Server")
    print("  ✓ Taranis Core")
    print("  ✓ Prefect Worker")
    print("="*60 + "\n")
    
    yield
    
    print("\n" + "="*60)
    print("Shutting down E2E Test Stack")
    print("="*60 + "\n")


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



# Test markers for organizing tests
def pytest_configure(config):
    """Register custom pytest markers for Prefect tests"""
    config.addinivalue_line("markers", "prefect: Prefect flow tests")
    config.addinivalue_line("markers", "presenter_flow: Presenter workflow tests")
    config.addinivalue_line("markers", "publisher_flow: Publisher workflow tests")
    config.addinivalue_line("markers", "connector_flow: Connector workflow tests")
    config.addinivalue_line("markers", "bot_flow: Bot workflow tests")
    config.addinivalue_line("markers", "slow: Slow running tests (flows)")
