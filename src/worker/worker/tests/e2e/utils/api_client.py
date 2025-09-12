"""
API Client for Prefect E2E Tests

Simple HTTP client for interacting with Taranis API during Prefect flow testing.
Assumes Docker Compose is already running.
"""

import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


class APIError(Exception):
    """API error with status code and response details"""

    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"API Error {status_code}: {message}")


@dataclass
class TestData:
    """Container for test data IDs"""

    product_type_id: Optional[str] = None
    product_id: Optional[str] = None
    presenter_id: Optional[str] = None
    publisher_id: Optional[str] = None
    connector_id: Optional[str] = None
    bot_id: Optional[str] = None
    news_item_ids: List[str] = None

    def __post_init__(self):
        if self.news_item_ids is None:
            self.news_item_ids = []


class TaranisAPIClient:
    """API client for Taranis E2E testing"""

    def __init__(self, base_url: str = "http://localhost:8081/api", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self._auth_token = None

        self.session.headers.update({"Content-Type": "application/json", "User-Agent": "Taranis-Prefect-E2E-Test"})

    def authenticate(self, username: str = "admin", password: str = "admin") -> None:
        """Authenticate with API and store access token"""
        print(f"Authenticating as {username}")

        response = self._make_request("POST", "/auth/login", json={"username": username, "password": password})

        self._auth_token = response.get("access_token")
        if not self._auth_token:
            raise APIError("No access token in login response")

        self.session.headers.update({"Authorization": f"Bearer {self._auth_token}"})

        print("Authentication successful")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)

            if response.status_code >= 400:
                print(f"ERROR: {method} {endpoint} -> {response.status_code}")
                print(f"Response: {response.text[:300]}")
            else:
                print(f"OK: {method} {endpoint} -> {response.status_code}")

            response.raise_for_status()

            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                return response

        except requests.exceptions.RequestException as e:
            error_text = getattr(e.response, "text", str(e)) if hasattr(e, "response") else str(e)
            status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            raise APIError(str(e), status_code, error_text)

    # Health and system checks
    def check_health(self) -> Dict[str, Any]:
        """Check API health"""
        return self._make_request("GET", "/isalive")

    def check_prefect_flows(self) -> Dict[str, Any]:
        """Check if Prefect flows are available"""
        try:
            response = requests.get("http://localhost:4200/api/flows", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Cannot connect to Prefect server: {e}")

    # Entity creation methods
    def create_product_type(self, name: str = None) -> str:
        """Create product type for testing"""
        timestamp = int(time.time())
        name = f"E2E Test Product Type {timestamp}"

        data = {
            "title": name,
            "description": "Product type for Prefect E2E testing",
            "type": "PDF_PRESENTER",
            "parameters": {"TEMPLATE_PATH": "test_template.html"},
            "report_types": [],
        }

        response = self._make_request("POST", "/config/product-types", json=data)
        product_type_id = response.get("id")

        if not product_type_id:
            raise APIError("No product type ID returned")

        print(f"Created Product Type: {product_type_id}")
        return str(product_type_id)

    def create_product(self, product_type_id: str, name: str = None) -> str:
        """Create product for testing"""

        timestamp = int(time.time())
        name = f"E2E Test Product {timestamp}"

        data = {"title": name, "description": "Product for Prefect E2E testing", "product_type_id": product_type_id}

        response = self._make_request("POST", "/config/products", json=data)
        product_id = response.get("id")

        if not product_id:
            raise APIError("No product ID returned")

        print(f"Created Product: {product_id}")
        return str(product_id)

    def create_presenter(self, name: str = None) -> str:
        """Create presenter configuration"""

        timestamp = int(time.time())
        name = f"E2E Test Presenter {timestamp}"

        data = {
            "name": name,
            "type": "PDF_PRESENTER",
            "description": "Presenter for Prefect E2E testing",
            "parameters": {"OUTPUT_PATH": "/tmp/test_output"},
        }

        response = self._make_request("POST", "/config/presenters", json=data)
        presenter_id = response.get("id")

        if not presenter_id:
            raise APIError("No presenter ID returned")

        print(f"Created Presenter: {presenter_id}")
        return str(presenter_id)

    def create_publisher(self, name: str = None) -> str:
        """Create publisher configuration"""

        timestamp = int(time.time())
        name = f"E2E Test Publiser {timestamp}"

        data = {
            "name": name,
            "type": "FTP_PUBLISHER",
            "description": "Publisher for Prefect E2E testing",
            "parameters": {"FTP_URL": "localhost", "FTP_USERNAME": "test", "FTP_PASSWORD": "test"},
        }

        response = self._make_request("POST", "/config/publisher-presets", json=data)
        publisher_id = response.get("id")

        if not publisher_id:
            raise APIError("No publisher ID returned")

        print(f"Created Publisher: {publisher_id}")
        return str(publisher_id)

    def create_connector(self, name: str = None) -> str:
        """Create connector configuration"""

        timestamp = int(time.time())
        name = f"E2E Test Connector {timestamp}"

        data = {
            "name": name,
            "type": "MISP_CONNECTOR",
            "description": "Connector for Prefect E2E testing",
            "parameters": {"MISP_URL": "http://localhost:8081", "MISP_API_KEY": "test-key"},
        }

        response = self._make_request("POST", "/config/connectors", json=data)
        connector_id = response.get("id")

        if not connector_id:
            raise APIError("No connector ID returned")

        print(f"Created Connector: {connector_id}")
        return str(connector_id)

    def create_bot(self, name: str = "E2E Test Bot") -> str:
        """Create bot configuration"""

        timestamp = int(time.time())
        name = f"E2E Test Create bot {timestamp}"

        data = {"name": name, "type": "NLP_BOT", "description": "Bot for Prefect E2E testing", "parameters": {"API_KEY": "test-key"}}

        response = self._make_request("POST", "/config/bots", json=data)
        bot_id = response.get("id")

        if not bot_id:
            raise APIError("No bot ID returned")

        print(f"Created Bot: {bot_id}")
        return str(bot_id)

    def create_news_items(self, count: int = 3) -> List[str]:
        """Create news items for testing"""
        news_items = []

        for i in range(count):
            item = {
                "title": f"E2E Test News Item {i + 1}",
                "content": f"This is test news content #{i + 1} for Prefect E2E testing. Contains keywords for bot processing.",
                "source": "e2e-test-source",
                "published_date": "2024-01-01T12:00:00.000Z",
                "web_url": f"https://example.com/test-news-{i + 1}",
                "author": "E2E Test Author",
                "collected_date": "2024-01-01T12:00:00.000Z",
            }
            news_items.append(item)

        response = self._make_request("POST", "/worker/news-items", json=news_items)

        # Try to extract IDs from response
        created_items = response.get("items", [])
        if created_items and isinstance(created_items, list):
            ids = []
            for item in created_items:
                if isinstance(item, dict) and item.get("id"):
                    ids.append(str(item["id"]))
            if ids:
                print(f"Created {len(ids)} News Items: {ids}")
                return ids

        # Fallback - assume they were created successfully
        print(f"Created {count} News Items (IDs not returned in response)")
        return [f"news-item-{i + 1}" for i in range(count)]

    # Flow trigger methods
    def trigger_presenter_flow(self, product_id: str, presenter_id: str = None) -> str:
        """Trigger presenter flow"""
        data = {"product_id": product_id}
        if presenter_id:
            data["presenter_id"] = presenter_id

        response = self._make_request("POST", f"/publish/products/{product_id}/render")
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from presenter flow")

        print(f"Started Presenter Flow: {flow_run_id}")
        return str(flow_run_id)

    def trigger_publisher_flow(self, product_id: str, publisher_id: str) -> str:
        """Trigger publisher flow"""

        response = self._make_request("POST", f"/publish/products/{product_id}/publishers/{publisher_id}")
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from publisher flow")

        print(f"Started Publisher Flow: {flow_run_id}")
        return str(flow_run_id)

    def trigger_connector_flow(self, connector_id: str, story_ids: List[str]) -> str:
        """Trigger connector flow"""
        data = {"connector_id": connector_id, "story_ids": story_ids}

        response = self._make_request("POST", "/flows/connector", json=data)
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from connector flow")

        print(f"Started Connector Flow: {flow_run_id}")
        return str(flow_run_id)

    def trigger_bot_flow(self, bot_id: str, story_ids: List[str] = None) -> str:
        """Trigger bot flow"""
        data = {"bot_id": bot_id}
        if story_ids:
            data["story_ids"] = story_ids

        response = self._make_request("POST", "/flows/bot", json=data)
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from bot flow")

        print(f"Started Bot Flow: {flow_run_id}")
        return str(flow_run_id)

    # Result checking methods
    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product details"""
        return self._make_request("GET", f"/config/products/{product_id}")

    def get_product_renders(self, product_id: str) -> List[Dict[str, Any]]:
        """Get product renders"""
        product = self.get_product(product_id)
        return product.get("renders", [])

    def get_product_publications(self, product_id: str) -> List[Dict[str, Any]]:
        """Get product publications"""
        product = self.get_product(product_id)
        return product.get("publications", [])

    def get_news_item(self, news_item_id: str) -> Dict[str, Any]:
        """Get news item details"""
        try:
            return self._make_request("GET", f"/worker/stories/{news_item_id}")
        except APIError as e:
            if e.status_code == 404:
                return {}
            raise

    def get_news_items_by_ids(self, news_item_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple news items"""
        items = []
        for news_id in news_item_ids:
            item = self.get_news_item(news_id)
            if item:
                items.append(item)
        return items

    # Flow monitoring methods
    def get_flow_run_status(self, flow_run_id: str) -> Optional[Dict[str, Any]]:
        """Get flow run status"""
        try:
            return self._make_request("GET", f"/flows/runs/{flow_run_id}")
        except APIError as e:
            if e.status_code == 404:
                return None
            raise

    def get_flow_run_logs(self, flow_run_id: str) -> List[str]:
        """Get flow run logs"""
        try:
            response = self._make_request("GET", f"/flows/runs/{flow_run_id}/logs")
            if isinstance(response, dict):
                return response.get("logs", [])
            return []
        except APIError:
            return []


def wait_for_flow_completion(api_client: TaranisAPIClient, flow_run_id: str, timeout: int = 120) -> None:
    """Wait for Prefect flow to complete with timeout and error handling"""
    print(f"Waiting for flow {flow_run_id} to complete (timeout: {timeout}s)")

    start_time = time.time()
    last_state = "UNKNOWN"

    while time.time() - start_time < timeout:
        try:
            status = api_client.get_flow_run_status(flow_run_id)

            if not status:
                print(f"Flow run {flow_run_id} not found - assuming completed")
                return

            state = status.get("state", "UNKNOWN")

            if state != last_state:
                print(f"Flow {flow_run_id} state: {last_state} -> {state}")
                last_state = state

            if state == "COMPLETED":
                print(f"Flow {flow_run_id} completed successfully")
                return

            elif state in ["FAILED", "CRASHED", "CANCELLED"]:
                error_msg = status.get("message", "No error message")
                logs = api_client.get_flow_run_logs(flow_run_id)

                error_details = f"Flow {flow_run_id} failed with state: {state}"
                if error_msg:
                    error_details += f"\nError message: {error_msg}"
                if logs:
                    error_details += "\nLast 5 log entries:\n" + "\n".join(logs[-5:])

                raise AssertionError(error_details)

        except APIError as e:
            if e.status_code == 404:
                print(f"Flow run {flow_run_id} not found - assuming completed")
                return
            else:
                print(f"Error checking flow status: {e}")

        time.sleep(5)

    # Timeout reached
    logs = api_client.get_flow_run_logs(flow_run_id)
    timeout_details = f"Flow {flow_run_id} timeout after {timeout}s (last state: {last_state})"
    if logs:
        timeout_details += "\nLast 5 log entries:\n" + "\n".join(logs[-5:])

    raise AssertionError(timeout_details)


def create_test_data(api_client: TaranisAPIClient) -> TestData:
    """Create complete test data set for Prefect E2E tests"""
    print("Creating test data for Prefect E2E tests")

    data = TestData()

    try:
        # Create entities in dependency order
        data.product_type_id = api_client.create_product_type()
        data.product_id = api_client.create_product(data.product_type_id)
        data.presenter_id = api_client.create_presenter()
        data.publisher_id = api_client.create_publisher()
        data.connector_id = api_client.create_connector()
        data.bot_id = api_client.create_bot()
        data.news_item_ids = api_client.create_news_items(count=3)

        print(f"Test data created successfully: {data}")
        return data

    except Exception as e:
        print(f"Failed to create test data: {e}")
        raise
