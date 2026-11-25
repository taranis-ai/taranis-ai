from base64 import b64decode
from typing import Any

from models.product import WorkerProduct
from niquests import Response
from niquests.exceptions import Timeout
from rq.timeouts import JobTimeoutException

from worker.http_client import http_request
from worker.publishers.base_publisher import BasePublisher
from worker.publishers.network import PublisherNetworkTimeout, effective_network_timeout, is_network_timeout


def _discard_redirect_location(response: Response, **_kwargs) -> None:
    # Even with redirects disabled, Niquests reads the body to prepare Response.next when Location is present.
    # This publisher only uses the status. Leave the body unread so closing the response releases it immediately.
    response.headers.pop("Location", None)


class WebhookPublisher(BasePublisher):
    def __init__(self):
        super().__init__()
        self.type = "WEBHOOK_PUBLISHER"
        self.name = "Webhook Publisher"
        self.description = "Send a rendered product to a webhook endpoint"

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: WorkerProduct) -> dict[str, str]:
        parameters = self._extract_parameters(publisher)
        encoded = self._require_rendered_data(rendered_product)
        mime_type = rendered_product.mime_type or "application/octet-stream"
        # An explicit empty override also prevents ambient .netrc credentials from being selected.
        token = parameters["BEARER_TOKEN"]
        headers = {"Authorization": f"Bearer {token}" if token else None}
        body: dict[str, Any]
        if parameters["PAYLOAD_FORMAT"] == "raw":
            body = {"data": b64decode(encoded, validate=True)}
            headers["Content-Type"] = mime_type
        else:
            headers["Content-Type"] = "application/json"
            body = {"json": {"product_id": product["id"], "title": product["title"], "mime_type": mime_type, "data": encoded.decode("ascii")}}

        try:
            with http_request(
                "POST",
                parameters["WEBHOOK_URL"],
                external=True,
                follow_redirects=False,
                hooks={"response": [_discard_redirect_location]},
                headers=headers,
                timeout=effective_network_timeout(parameters),
                verify=True,
                stream=True,
                **body,
            ) as response:
                status = response.status_code
        except JobTimeoutException:
            raise
        except Exception as exc:
            if isinstance(exc, Timeout) or is_network_timeout(exc):
                raise PublisherNetworkTimeout("webhook_publisher", "delivery") from None
            raise RuntimeError("Webhook delivery failed") from None
        if status is None or not 200 <= status < 300:
            raise RuntimeError("Webhook endpoint rejected delivery")
        return {"message": "Webhook delivery accepted"}
