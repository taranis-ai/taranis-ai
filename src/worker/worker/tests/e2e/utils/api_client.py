"""
API Client for Prefect E2E Tests

Simple HTTP client for interacting with Taranis API during Prefect flow testing.
"""

import os
import requests
import time
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


class APIError(Exception):
    """API error with status code and response details"""

    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(f"API Error {status_code}: {message}")


def _join_url(base: str, path: str) -> str:
    """Join base + path without double slashes or trailing slash."""
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


@dataclass
class TestData:
    """Container for test data IDs"""
    __test__ = False

    product_type_id: Optional[str] = None
    product_id: Optional[str] = None
    presenter_id: Optional[str] = None
    publisher_id: Optional[str] = None
    connector_id: Optional[str] = None
    bot_id: Optional[str] = None
    news_item_ids: List[str] = None
    story_ids: List[str] = None

    def __post_init__(self):
        if self.news_item_ids is None:
            self.news_item_ids = []
        if self.story_ids is None:
            self.story_ids = []


class TaranisAPIClient:
    """API client for Taranis E2E testing"""

    def __init__(self, base_url: str = None, timeout: int = 30):
        if base_url is None:
            base_url = os.getenv("CORE_API_URL", "http://127.0.0.1:5000/api")

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
        url = _join_url(self.base_url, endpoint)
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
        """
        Return a structure compatible with tests by deriving flow "names" from
        registered deployments. Prefect 2 has no GET /flows that returns a list.
        """
        prefect_api = os.getenv("PREFECT_API_URL", "http://127.0.0.1:4200/api").rstrip("/")
        url = f"{prefect_api}/deployments/filter"

        try:
            resp = requests.post(url,json={}, timeout=self.timeout)
            resp.raise_for_status()
            deployments = resp.json() or []
        except Exception as e:
            print(f"Warning: Cannot list Prefect deployments: {e}")
            return {"flows": []}

        flows_list = []
        for d in deployments:
            entrypoint = d.get("entrypoint", "")
            func = entrypoint.split(":")[-1] if ":" in entrypoint else ""
            if not func:
                m = re.search(r'/flows/([a-zA-Z0-9_]+)', entrypoint)
                func = (m.group(1) if m else "").strip()

            # Convert function_name to hyphenated flow name used by tests
            flow_name = func.replace("_", "-") if func else None

            if flow_name:
                flows_list.append({
                    "name": flow_name,
                    "deployment": d.get("name"),
                    "entrypoint": entrypoint,
                    "id": d.get("id"),
                })

        return {"flows": flows_list}


    # Entity creation methods
    def create_product_type(self, name: str = None) -> str:
        """Create product type for testing"""
        import random
        timestamp = int(time.time())
        random_suffix = random.randint(1000, 9999)
        name = f"E2E Test Product Type {timestamp}-{random_suffix}"

        data = {
            "title": name,
            "description": "Product type for Prefect E2E testing",
            "type": "TEXT_PRESENTER",
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

        response = self._make_request("POST", "/publish/products", json=data)
        product_id = response.get("id")

        if not product_id:
            raise APIError("No product ID returned")

        print(f"Created Product: {product_id}")
        return str(product_id)


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

        data = {"name": name, "type": "TAGGING_BOT", "description": "Bot for Prefect E2E testing", "parameters": {}}

        response = self._make_request("POST", "/config/bots", json=data)
        bot_id = response.get("id")

        if not bot_id:
            raise APIError("No bot ID returned")

        print(f"Created Bot: {bot_id}")
        return str(bot_id)

    def create_news_items(self, count: int = 3) -> tuple[List[str], List[str]]:
        """
        Create news items for testing
        Returns: (news_item_ids, story_ids)
        """
        news_item_ids = []
        story_ids_set = set()  # Use set to avoid duplicates since multiple items might go to same story

        for i in range(count):
            import hashlib
            import random
            # Make each news item truly unique by adding timestamp and random component
            timestamp_ms = time.time_ns()  # Use nanoseconds for higher resolution
            random_suffix = random.randint(10000, 99999)
            unique_string = f"test-news-{i+1}-{timestamp_ms}-{random_suffix}"
            hash_value = hashlib.sha256(unique_string.encode()).hexdigest()

            item = {
                "title": f"E2E Test News Item {i + 1} - {timestamp_ms}",
                "content": f"This is test news content #{i + 1} for Prefect E2E testing. Unique ID: {unique_string}",
                "link":      f"https://example.com/test-news-{i+1}-{timestamp_ms}",
                "source": "e2e-test-source",
                "author": "E2E Test Author",
                "published": "2024-01-01T12:00:00.000Z",
                "collected": "2024-01-01T12:00:00Z",
                "hash": hash_value,
                "language": "en",
                "review": "Test review",
                "osint_source_id": "manual",
                "id": unique_string,
                "attributes": []

            }
            try:

                response = self._make_request("POST", "/assess/news-items", json=item)
                # API returns news_item_ids and story_id
                if isinstance(response, dict):
                    returned_news_item_ids = response.get("news_item_ids", [])
                    story_id = response.get("story_id")

                    if returned_news_item_ids and len(returned_news_item_ids) > 0:
                        item_id = returned_news_item_ids[0]
                    else:
                        item_id = None

                    if story_id:
                        story_ids_set.add(str(story_id))
                else:
                    item_id = None

                if not item_id:
                    raise APIError(f"No news_item_ids returned when creating news item {i + 1}. Response: {response}")
                news_item_ids.append(str(item_id))
            except APIError as e:
                print(f"⚠ Failed to create news item {i + 1}: {e}")
                raise

        story_ids = list(story_ids_set)
        print(f"Created {len(news_item_ids)} News Items: {news_item_ids}")
        print(f"Created {len(story_ids)} Stories: {story_ids}")
        return news_item_ids, story_ids

    # Flow trigger methods
    def trigger_presenter_flow(self, product_id: str, presenter_id: str = None) -> str:
        """Trigger presenter flow (Core chooses presenter internally)"""
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
        """Trigger connector flow (if exposed)"""
        response = self._make_request("POST", "/flows/connector", json={"connector_id": connector_id, "story_ids": story_ids})
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from connector flow")

        print(f"Started Connector Flow: {flow_run_id}")
        return str(flow_run_id)

    def trigger_bot_flow(self, bot_id: str, story_ids: List[str] = None) -> str:
        """Trigger bot flow using the execute endpoint"""
        payload = {"story_ids": story_ids} if story_ids else None
        response = self._make_request("POST", f"/config/bots/{bot_id}/execute", json=payload)
        flow_run_id = response.get("flow_run_id") or response.get("id")

        if not flow_run_id:
            raise APIError("No flow run ID returned from bot flow")

        print(f"Started Bot Flow: {flow_run_id}")
        return str(flow_run_id)

    # Result checking methods
    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product details"""
        return self._make_request("GET", f"/publish/products/{product_id}")

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

def wait_for_flow_completion(api_client: TaranisAPIClient, flow_run_id: str, timeout: int = 120) -> None:
    """
    Wait for Prefect flow to complete by polling Prefect's API directly.
    """
    prefect_api = os.getenv("PREFECT_API_URL", "http://127.0.0.1:4200/api").rstrip("/")
    url = f"{prefect_api}/flow_runs/{flow_run_id}"  # no trailing slash after id
    terminal_states = {"COMPLETED", "FAILED", "CANCELLED", "CRASHED"}
    start_time = time.time()
    last_state = None

    print(f"Waiting for flow {flow_run_id} to complete (timeout: {timeout}s)")
    print(f"Polling Prefect API at: {url}")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            # Try different possible state field names in Prefect API
            state = (
                (data.get("state") or {}).get("type") or
                data.get("state_name") or
                data.get("state")
            )

            # Log state changes
            if state != last_state:
                print(f"Flow {flow_run_id} state: {last_state} → {state}")
                last_state = state

            # Check terminal state
            if state in terminal_states:
                if state == "COMPLETED":
                    print(f"✓ Flow {flow_run_id} completed successfully")
                    return
                raise AssertionError(f"Flow {flow_run_id} finished with state: {state}")

        except requests.RequestException as e:
            print(f"⚠ Error polling Prefect API: {e}")

        time.sleep(1.0)

    # Timeout reached
    raise AssertionError(f"Timeout waiting for flow {flow_run_id} after {timeout}s (last state: {last_state})")


def create_test_data(api_client: TaranisAPIClient) -> TestData:
    """Create test data set for Prefect E2E tests"""
    print("Creating test data for Prefect E2E tests")

    data = TestData()

    # Create entities in dependency order
    data.product_type_id = api_client.create_product_type()
    data.product_id = api_client.create_product(data.product_type_id)

    # Get first available presenter
    try:
        response = api_client._make_request("GET", "/config/presenters")

        presenters = []
        if isinstance(response, list):
            presenters = response
        elif isinstance(response, dict):
            # Try common containers (depends on API format)
            for key in ("items", "presenters", "data", "results"):
                if isinstance(response.get(key), list):
                    presenters = response[key]
                    break

        if presenters:
            data.presenter_id = str(presenters[0].get("id"))
            print(f" Using presenter: {data.presenter_id}")
        else:
            print(" No presenters found")
            data.presenter_id = None

    except Exception as e:
        print(f" Could not get presenters: {e}")
        data.presenter_id = None

    # Continue creating other test entities
    data.publisher_id = api_client.create_publisher()
    data.connector_id = api_client.create_connector()
    data.bot_id = api_client.create_bot()
    data.news_item_ids, data.story_ids = api_client.create_news_items(count=3)

    print(" Test data created successfully")
    return data
