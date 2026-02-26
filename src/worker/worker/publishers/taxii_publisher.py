import json
from typing import Any

from models.product import WorkerProduct as Product
from requests.auth import AuthBase

from .base_publisher import BasePublisher


class BearerAuth(AuthBase):
    def __init__(self, token: str):
        self.token = token

    def __call__(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class TAXIIPublisher(BasePublisher):
    REQUIRED_PARAMETERS = ("TAXII_COLLECTION_ID", "AUTH_TYPE")

    def __init__(self):
        super().__init__()
        self.type = "TAXII_PUBLISHER"
        self.name = "TAXII Publisher"
        self.description = "Publisher for pushing STIX objects to a TAXII 2.1 collection"

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> dict[str, Any]:
        del product  # Presenter already produced the final STIX bundle.

        parameters = self._extract_parameters(publisher)
        self._validate_auth_parameters(parameters)

        stix_objects = self._extract_stix_objects_from_bundle(rendered_product)
        collection = self._get_collection(parameters)
        status = collection.add_objects({"objects": stix_objects})

        return {
            "status": "success",
            "collection_id": parameters["TAXII_COLLECTION_ID"],
            "objects_sent": len(stix_objects),
            "taxii_status": self._status_to_dict(status),
        }

    def _get_collection(self, parameters: dict[str, Any]):
        try:
            from taxii2client.v21 import Collection, Server
        except ImportError as exc:
            raise RuntimeError("taxii2-client is required for TAXII publisher support") from exc

        client_kwargs = self._build_client_kwargs(parameters)
        api_root_url = str(parameters.get("TAXII_API_ROOT_URL") or "").strip()

        if not api_root_url:
            discovery_url = str(parameters.get("TAXII_DISCOVERY_URL") or "").strip()
            if not discovery_url:
                raise ValueError("Either TAXII_API_ROOT_URL or TAXII_DISCOVERY_URL is required")

            server = Server(discovery_url, **client_kwargs)
            api_roots = getattr(server, "api_roots", None) or []
            if not api_roots:
                raise ValueError("No TAXII API root discovered")
            api_root_url = str(api_roots[0].url)

        collection_url = f"{api_root_url.rstrip('/')}/collections/{parameters['TAXII_COLLECTION_ID']}/"
        return Collection(collection_url, **client_kwargs)

    def _build_client_kwargs(self, parameters: dict[str, Any]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"verify": parameters.get("SSL_VERIFY") == "true"}

        if proxy_server := parameters.get("PROXY_SERVER"):
            kwargs["proxies"] = {
                "http": str(proxy_server),
                "https": str(proxy_server),
            }

        auth_type = str(parameters.get("AUTH_TYPE", "")).lower()
        if auth_type == "basic":
            kwargs["user"] = str(parameters["USERNAME"])
            kwargs["password"] = str(parameters["PASSWORD"])
        elif auth_type == "bearer":
            kwargs["auth"] = BearerAuth(str(parameters["API_TOKEN"]))
        else:
            raise ValueError("AUTH_TYPE must be either 'basic' or 'bearer'")

        return kwargs

    def _validate_auth_parameters(self, parameters: dict[str, Any]) -> None:
        auth_type = str(parameters.get("AUTH_TYPE", "")).lower()
        if auth_type == "basic":
            if not parameters.get("USERNAME") or not parameters.get("PASSWORD"):
                raise ValueError("AUTH_TYPE basic requires USERNAME and PASSWORD")
            return

        if auth_type == "bearer":
            if not parameters.get("API_TOKEN"):
                raise ValueError("AUTH_TYPE bearer requires API_TOKEN")
            return

        raise ValueError("AUTH_TYPE must be either 'basic' or 'bearer'")

    def _extract_stix_objects_from_bundle(self, rendered_product: Product) -> list[dict[str, Any]]:
        if not rendered_product.data:
            raise ValueError("Rendered product data is empty")

        try:
            payload = json.loads(rendered_product.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Rendered product must be valid JSON") from exc

        if not isinstance(payload, dict) or payload.get("type") != "bundle":
            raise ValueError("Rendered product must be a STIX bundle")

        objects = payload.get("objects")
        if not isinstance(objects, list) or not objects:
            raise ValueError("STIX bundle has no objects")

        if not all(isinstance(obj, dict) for obj in objects):
            raise ValueError("STIX bundle objects must be JSON objects")

        return objects

    @staticmethod
    def _status_to_dict(status: Any) -> dict[str, Any]:
        if isinstance(status, dict):
            return status

        if hasattr(status, "id") or hasattr(status, "status"):
            return {
                "id": getattr(status, "id", None),
                "status": getattr(status, "status", None),
                "failure_count": getattr(status, "failure_count", None),
                "success_count": getattr(status, "success_count", None),
            }

        return {"raw": str(status)}
