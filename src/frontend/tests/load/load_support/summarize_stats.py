from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PAGE_REQUEST_TYPE = "PAGE"

SUMMARY_COLUMNS = (
    ("Name", "name"),
    ("Requests", "request_count"),
    ("Failures", "failure_count"),
    ("Avg (ms)", "average_response_time"),
    ("P50 (ms)", "p50"),
    ("P95 (ms)", "p95"),
    ("P99 (ms)", "p99"),
    ("Max (ms)", "max_response_time"),
)


def parse_float(value: str) -> float:
    if not value:
        return 0.0
    return float(value)


def parse_int(value: str) -> int:
    if not value:
        return 0
    return int(float(value))


def load_page_rows(stats_path: Path) -> list[dict[str, object]]:
    if not stats_path.exists():
        raise FileNotFoundError(f"Locust stats file not found: {stats_path}")

    with stats_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            if row.get("Type") != PAGE_REQUEST_TYPE:
                continue
            rows.append(
                {
                    "name": row["Name"],
                    "request_count": parse_int(row["Request Count"]),
                    "failure_count": parse_int(row["Failure Count"]),
                    "median_response_time": parse_float(row["Median Response Time"]),
                    "average_response_time": parse_float(row["Average Response Time"]),
                    "min_response_time": parse_float(row["Min Response Time"]),
                    "max_response_time": parse_float(row["Max Response Time"]),
                    "p50": parse_float(row["50%"]),
                    "p95": parse_float(row["95%"]),
                    "p99": parse_float(row["99%"]),
                }
            )

    rows.sort(
        key=lambda row: (
            float(row["p95"]),
            float(row["average_response_time"]),
            float(row["max_response_time"]),
        ),
        reverse=True,
    )
    return rows


def format_metric(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.1f}"


def build_markdown(rows: list[dict[str, object]]) -> str:
    lines = [
        "# UX Timings Summary",
        "",
        "Sorted by `p95` descending for Locust `PAGE` events.",
        "",
    ]

    if not rows:
        lines.append("No `PAGE` timing rows were found in `locust_stats.csv`.")
        return "\n".join(lines) + "\n"

    header = "| " + " | ".join(column for column, _ in SUMMARY_COLUMNS) + " |"
    separator = "| " + " | ".join("---:" if column != "Name" else "---" for column, _ in SUMMARY_COLUMNS) + " |"
    lines.extend([header, separator])

    for row in rows:
        values = []
        for _, key in SUMMARY_COLUMNS:
            value = row[key]
            values.append(str(value) if key == "name" else format_metric(value))
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines) + "\n"


def write_outputs(rows: list[dict[str, object]], markdown_path: Path, json_path: Path) -> str:
    markdown = build_markdown(rows)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return markdown


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage: python -m tests.load.load_support.summarize_stats <locust_stats.csv> <ux-timings-summary.md> <ux-timings-summary.json>",
            file=sys.stderr,
        )
        return 1

    stats_path = Path(argv[1])
    markdown_path = Path(argv[2])
    json_path = Path(argv[3])

    rows = load_page_rows(stats_path)
    markdown = write_outputs(rows, markdown_path, json_path)
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
