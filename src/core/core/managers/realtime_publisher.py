import time
import uuid
from datetime import UTC, datetime
from typing import Any

import requests

from core.config import Config
from core.log import logger


class RealtimePublisher:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.last_warning_at = float("-inf")

    def publish(
        self,
        channel: str,
        event_type: str,
        change: str,
        *,
        resource: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        if not Config.REALTIME_ENABLED:
            return False

        event = {
            "v": 1,
            "id": str(uuid.uuid7()),
            "type": event_type,
            "occurred_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "change": change,
            "data": data or {},
        }
        if resource:
            event["resource"] = resource

        started = time.monotonic()
        try:
            response = self.session.post(
                f"{Config.CENTRIFUGO_API_URL.rstrip('/')}/api/broadcast",
                headers={"X-API-Key": Config.CENTRIFUGO_API_KEY.get_secret_value()},
                json={"channels": [channel], "data": event},
                timeout=(0.2, 0.3),
            )
            response.raise_for_status()
            responses = response.json().get("result", {}).get("responses")
            if not isinstance(responses, list) or len(responses) != 1 or any(item.get("error") for item in responses):
                raise ValueError("Centrifugo rejected the broadcast")
        except Exception as error:
            now = time.monotonic()
            if now - self.last_warning_at >= 60:
                self.last_warning_at = now
                logger.warning(
                    "realtime_publish_failed %s",
                    {
                        "event_id": event["id"],
                        "event_type": event_type,
                        "audience": channel.partition(":")[0],
                        "duration_ms": round((now - started) * 1000, 1),
                        "failure": type(error).__name__,
                    },
                )
            return False

        return True

    def assess_changed(self) -> bool:
        return self.publish("global:events", "assess.changed", "invalidated")

    def broadcast_notification(self, message: str) -> bool:
        return self.publish(
            "global:events",
            "notification.broadcast",
            "created",
            data={"message": message, "persistent": True},
        )

    def connected_clients(self) -> list[dict[str, str]] | None:
        if not Config.REALTIME_ENABLED:
            return None

        try:
            response = self.session.post(
                f"{Config.CENTRIFUGO_API_URL.rstrip('/')}/api/presence",
                headers={"X-API-Key": Config.CENTRIFUGO_API_KEY.get_secret_value()},
                json={"channel": "global:events"},
                timeout=(0.2, 0.3),
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("error"):
                raise ValueError("Centrifugo rejected the presence request")
            result = payload.get("result")
            presence = result.get("presence") if isinstance(result, dict) else None
            if not isinstance(presence, dict):
                raise TypeError("Centrifugo returned invalid presence data")
            return sorted(
                (
                    {
                        "client_id": str(info.get("client") or client_id),
                        "user_id": str(info.get("user") or ""),
                    }
                    for client_id, info in presence.items()
                    if isinstance(info, dict)
                ),
                key=lambda client: (client["user_id"], client["client_id"]),
            )
        except (requests.RequestException, TypeError, ValueError) as error:
            logger.warning("realtime_presence_failed %s", {"failure": type(error).__name__})
            return None

    def report_item_changed(self, report_item_id: str, organization_id: str, change: str = "updated") -> bool:
        return self.publish(
            f"org:{organization_id}",
            "report.item.changed",
            change,
            resource={"kind": "report_item", "id": report_item_id},
        )

    def report_lock_changed(self, report_item_id: str, organization_id: str) -> bool:
        return self.publish(
            f"org:{organization_id}",
            "report.lock.changed",
            "updated",
            resource={"kind": "report_item", "id": report_item_id},
        )

    def product_rendered(self, product_id: str, user_id: str, status: str) -> bool:
        return self.publish(
            f"user:#{user_id}",
            "product.rendered",
            "completed",
            resource={"kind": "product", "id": product_id},
            data={"status": status},
        )

    def osint_source_preview_finished(self, source_id: str, user_id: str, status: str) -> bool:
        return self.publish(
            f"user:#{user_id}",
            "osint_source.preview.finished",
            "completed",
            resource={"kind": "osint_source", "id": source_id},
            data={"status": status},
        )

    def chat_turn_updated(
        self,
        user_id: str,
        turn_id: str,
        sequence: int,
        stage: str,
        content: str,
    ) -> bool:
        return self.publish(
            f"user:#{user_id}",
            "chat.turn.updated",
            "updated",
            data={
                "turn_id": turn_id,
                "sequence": sequence,
                "stage": stage,
                "content": content,
            },
        )


realtime_publisher = RealtimePublisher()
