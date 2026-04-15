import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class EndpointSnapshot:
    name: str
    url: str
    status_code: int
    body_subset: dict[str, Any]


def read_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def snapshot_endpoint(name: str, url: str) -> EndpointSnapshot:
    response = requests.get(url, timeout=10)
    body_subset: dict[str, Any] = {}
    with_body = response.headers.get("content-type", "").startswith("application/json")
    if with_body:
        payload = response.json()
        if name == "core_isalive":
            body_subset = {"isalive": payload.get("isalive")}
        elif name == "core_health":
            body_subset = {"healthy": payload.get("healthy"), "services": payload.get("services", {})}
    return EndpointSnapshot(name=name, url=url, status_code=response.status_code, body_subset=body_subset)


def build_current_snapshots() -> list[EndpointSnapshot]:
    core_api_url = read_env("CORE_API_URL", "http://core:8080/api")
    frontend_url = read_env("FRONTEND_URL", "http://ingress:8080/frontend")
    return [
        snapshot_endpoint("core_isalive", f"{core_api_url}/isalive"),
        snapshot_endpoint("core_health", f"{core_api_url}/health"),
        snapshot_endpoint("frontend_health", f"{frontend_url}/health"),
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def record_baseline(path: Path) -> int:
    snapshots = build_current_snapshots()
    write_json(path, {"snapshots": [asdict(snapshot) for snapshot in snapshots]})
    print(f"Wrote recovery baseline to {path}")
    return 0


def snapshot_matches(expected: EndpointSnapshot, actual: EndpointSnapshot) -> bool:
    return expected.status_code == actual.status_code and expected.body_subset == actual.body_subset


def verify_recovery(baseline_path: Path, output_path: Path, timeout_seconds: int) -> int:
    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    expected = [EndpointSnapshot(**item) for item in baseline_payload["snapshots"]]

    deadline = time.monotonic() + timeout_seconds
    last_actual = build_current_snapshots()
    while time.monotonic() < deadline:
        last_actual = build_current_snapshots()
        if all(snapshot_matches(expected_item, actual_item) for expected_item, actual_item in zip(expected, last_actual, strict=True)):
            write_json(
                output_path,
                {
                    "baseline": [asdict(item) for item in expected],
                    "actual": [asdict(item) for item in last_actual],
                    "recovered": True,
                },
            )
            print(f"Recovery matched baseline within {timeout_seconds}s")
            return 0
        time.sleep(2)

    write_json(
        output_path,
        {
            "baseline": [asdict(item) for item in expected],
            "actual": [asdict(item) for item in last_actual],
            "recovered": False,
        },
    )
    print("Recovery check failed to reach baseline state in time")
    return 1


def main() -> int:
    mode = os.sys.argv[1] if len(os.sys.argv) > 1 else "verify"
    baseline_path = Path(read_env("RECOVERY_BASELINE_PATH", "/artifacts/recovery-baseline.json"))
    output_path = Path(read_env("RECOVERY_OUTPUT_PATH", "/artifacts/recovery-results.json"))
    timeout_seconds = int(read_env("RECOVERY_TIMEOUT_SECONDS", "60"))

    if mode == "record-baseline":
        return record_baseline(baseline_path)
    if mode == "verify":
        return verify_recovery(baseline_path, output_path, timeout_seconds)
    raise RuntimeError(f"Unsupported recovery mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
